from __future__ import annotations

import os
import hmac
import hashlib
import urllib.parse
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from apps.backend.db import get_supabase
from apps.backend.services.shopify_backfill import enqueue_backfill


router = APIRouter(prefix="/shopify", tags=["shopify"])

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
APP_URL = os.getenv("APP_URL")  # e.g. https://exclusivity-backend.onrender.com

# Scopes already configured in Partners UI; we record what Shopify reports.
DEFAULT_SCOPES = os.getenv("SHOPIFY_SCOPES", "read_orders,read_customers,read_inventory")


def _verify_hmac(query: dict) -> bool:
    """
    Verifies Shopify OAuth callback HMAC.
    Shopify sends hmac over query string (excluding 'hmac' itself).
    """
    if not SHOPIFY_API_SECRET:
        return False
    received = query.get("hmac", "")
    items = []
    for k in sorted(query.keys()):
        if k == "hmac":
            continue
        v = query[k]
        items.append(f"{k}={v}")
    msg = "&".join(items).encode("utf-8")
    digest = hmac.new(SHOPIFY_API_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, received)


@router.get("/oauth/callback")
async def oauth_callback(request: Request, background: BackgroundTasks):
    """
    OAuth callback endpoint. On success:
    - stores integration token
    - ensures merchant_brand record exists
    - enqueues backfill automatically
    """
    if not SHOPIFY_API_KEY or not SHOPIFY_API_SECRET:
        raise HTTPException(500, "Shopify OAuth not configured (missing env vars)")

    q = dict(request.query_params)

    if not _verify_hmac(q):
        raise HTTPException(400, "Invalid OAuth signature")

    code = q.get("code")
    shop = q.get("shop")
    state = q.get("state")  # expected to be merchant_id (simple beta model)
    scope = q.get("scope", DEFAULT_SCOPES)

    if not code or not shop or not state:
        raise HTTPException(400, "Missing required OAuth params")

    merchant_id = state.strip()
    shop_domain = shop.strip().lower()

    # Exchange code for token
    import requests
    token_url = f"https://{shop_domain}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code": code,
    }

    try:
        r = requests.post(token_url, json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()
        access_token = data.get("access_token")
        scopes = data.get("scope", scope)
        if not access_token:
            raise Exception("Missing access_token in response")
    except Exception as e:
        raise HTTPException(500, f"OAuth token exchange failed: {e}")

    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    # Upsert merchant integration
    sb.table("merchant_integrations").upsert({
        "merchant_id": merchant_id,
        "provider": "shopify",
        "shop_domain": shop_domain,
        "access_token": access_token,
        "scopes": scopes,
    }, on_conflict="merchant_id,provider").execute()

    # Ensure merchant brand row exists (theme + naming captured during onboarding)
    existing = sb.table("merchant_brand").select("*").eq("merchant_id", merchant_id).limit(1).execute()
    if not existing.data:
        sb.table("merchant_brand").insert({
            "merchant_id": merchant_id,
            "shop_domain": shop_domain,
            "program_name": "Loyalty Program",
            "unit_name_singular": "Point",
            "unit_name_plural": "Points",
            "onboarding_completed": False,
        }).execute()
    else:
        sb.table("merchant_brand").update({"shop_domain": shop_domain}).eq("merchant_id", merchant_id).execute()

    # Enqueue backfill automatically (non-optional)
    enqueue_backfill(merchant_id, shop_domain)

    # Kick off first backfill page in the background immediately (fast and safe)
    from apps.backend.services.shopify_backfill import run_backfill_once
    background.add_task(run_backfill_once, merchant_id)

    # Return a stable response. Frontend can poll /shopify/backfill/status and /onboarding/*
    return JSONResponse(content={
        "ok": True,
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "message": "Installed. Backfill has started. Proceed to onboarding.",
        "next": {
            "backfill_status": "/shopify/backfill/status?merchant_id=" + urllib.parse.quote(merchant_id),
            "onboarding_questions": "/onboarding/questions?merchant_id=" + urllib.parse.quote(merchant_id),
        }
    })
