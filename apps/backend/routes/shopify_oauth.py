from __future__ import annotations

import os
import hmac
import hashlib
import urllib.parse
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from apps.backend.db import get_supabase
from apps.backend.services.shopify_backfill import enqueue_backfill, run_backfill_once
from apps.backend.services.shopify_brand_ingest import ingest_brand
from apps.backend.services.shopify_catalog_snapshot import snapshot_catalog
from apps.backend.services.pricing_buffer import generate_pricing_recommendations


router = APIRouter(prefix="/shopify", tags=["shopify"])

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")
DEFAULT_SCOPES = os.getenv("SHOPIFY_SCOPES", "read_orders,read_customers,read_inventory")


def _verify_hmac(query: dict) -> bool:
    if not SHOPIFY_API_SECRET:
        return False
    received = query.get("hmac", "")
    items = []
    for k in sorted(query.keys()):
        if k == "hmac":
            continue
        items.append(f"{k}={query[k]}")
    msg = "&".join(items).encode("utf-8")
    digest = hmac.new(SHOPIFY_API_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, received)


@router.get("/oauth/callback")
async def oauth_callback(request: Request, background: BackgroundTasks):
    if not SHOPIFY_API_KEY or not SHOPIFY_API_SECRET:
        raise HTTPException(500, "Shopify OAuth not configured (missing env vars)")

    q = dict(request.query_params)
    if not _verify_hmac(q):
        raise HTTPException(400, "Invalid OAuth signature")

    code = q.get("code")
    shop = q.get("shop")
    state = q.get("state")  # merchant_id (beta: simple)
    scope = q.get("scope", DEFAULT_SCOPES)

    if not code or not shop or not state:
        raise HTTPException(400, "Missing required OAuth params")

    merchant_id = state.strip()
    shop_domain = shop.strip().lower()

    # Exchange code for token
    import requests
    token_url = f"https://{shop_domain}/admin/oauth/access_token"
    payload = {"client_id": SHOPIFY_API_KEY, "client_secret": SHOPIFY_API_SECRET, "code": code}

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

    # Upsert integration
    sb.table("merchant_integrations").upsert({
        "merchant_id": merchant_id,
        "provider": "shopify",
        "shop_domain": shop_domain,
        "access_token": access_token,
        "scopes": scopes,
    }, on_conflict="merchant_id,provider").execute()

    # Ensure brand row exists
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

    # 1) Backfill begins immediately (required)
    enqueue_backfill(merchant_id, shop_domain)
    background.add_task(run_backfill_once, merchant_id)

    # 2) Brand + theme ingestion (best-effort)
    background.add_task(ingest_brand, merchant_id)

    # 3) Catalog snapshot (best-effort)
    background.add_task(snapshot_catalog, merchant_id)

    # 4) Pricing buffer recommendations (flat buffer v1)
    background.add_task(generate_pricing_recommendations, merchant_id)

    return JSONResponse(content={
        "ok": True,
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "message": "Installed. Backfill started. Brand and pricing intelligence queued. Proceed to onboarding.",
        "next": {
            "backfill_status": "/shopify/backfill/status?merchant_id=" + urllib.parse.quote(merchant_id),
            "brand_status": "/brand/status?merchant_id=" + urllib.parse.quote(merchant_id),
            "onboarding_questions": "/onboarding/questions?merchant_id=" + urllib.parse.quote(merchant_id),
            "pricing_latest": "/pricing/recommendations/latest?merchant_id=" + urllib.parse.quote(merchant_id),
        }
    })
