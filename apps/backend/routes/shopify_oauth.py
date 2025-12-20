from __future__ import annotations

import os
import hmac
import hashlib
from typing import Dict, Any, Optional

import requests
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from apps.backend.db import get_supabase
from apps.backend.services.merchant_identity import (
    get_or_create_merchant_identity_for_shop,
    upsert_integration,
)

router = APIRouter(tags=["shopify"])

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET")


def _verify_hmac(query: Dict[str, str]) -> bool:
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


def _best_effort_background(background: BackgroundTasks, fn, *args, **kwargs):
    """
    Adds background task if fn exists; never raises.
    """
    try:
        if fn:
            background.add_task(fn, *args, **kwargs)
    except Exception:
        return


@router.get("/oauth/callback")
async def oauth_callback(request: Request, background: BackgroundTasks):
    """
    Canonical install entrypoint:
    - Verify Shopify HMAC
    - Exchange code for access token
    - Resolve/create canonical merchant UUID
    - Upsert integration mapping
    - Ensure baseline merchant_brand row exists
    - Kick backfill + brand ingest + catalog snapshot + pricing recs (best-effort)
    """
    if not SHOPIFY_API_KEY or not SHOPIFY_API_SECRET:
        raise HTTPException(500, "Shopify OAuth not configured (missing SHOPIFY_API_KEY/SHOPIFY_API_SECRET)")

    q = dict(request.query_params)
    if not _verify_hmac(q):
        raise HTTPException(400, "Invalid OAuth signature")

    code = q.get("code")
    shop = q.get("shop")
    scope = q.get("scope", "")

    if not code or not shop:
        raise HTTPException(400, "Missing required OAuth params: code/shop")

    shop_domain = shop.lower().strip()

    # Exchange code for token
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

    # Resolve/create canonical merchant UUID
    ident = get_or_create_merchant_identity_for_shop(shop_domain, provider="shopify")
    merchant_id = ident.merchant_id

    # Upsert integration mapping
    up = upsert_integration(
        merchant_id=merchant_id,
        provider="shopify",
        shop_domain=shop_domain,
        access_token=access_token,
        scopes=scopes or "",
    )
    if not up.get("ok"):
        raise HTTPException(500, f"Integration upsert failed: {up.get('error')}")

    # Ensure baseline merchant_brand exists
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    try:
        br = sb.table("merchant_brand").select("*").eq("merchant_id", merchant_id).limit(1).execute()
        if not br.data:
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
    except Exception:
        # non-fatal; install can still proceed
        pass

    # --- BEST-EFFORT: Kick install automation tasks ---
    # Backfill (if module exists)
    enqueue_backfill = None
    run_backfill_once = None
    try:
        from apps.backend.services.shopify_backfill import enqueue_backfill as _eb, run_backfill_once as _rb  # type: ignore
        enqueue_backfill, run_backfill_once = _eb, _rb
    except Exception:
        pass

    try:
        if enqueue_backfill:
            enqueue_backfill(merchant_id, shop_domain)  # type: ignore
    except Exception:
        pass

    _best_effort_background(background, run_backfill_once, merchant_id)

    # Brand ingest
    ingest_brand = None
    try:
        from apps.backend.services.shopify_brand_ingest import ingest_brand as _ingest  # type: ignore
        ingest_brand = _ingest
    except Exception:
        pass
    _best_effort_background(background, ingest_brand, merchant_id)

    # Catalog snapshot
    snapshot_catalog = None
    try:
        from apps.backend.services.shopify_catalog_snapshot import snapshot_catalog as _snap  # type: ignore
        snapshot_catalog = _snap
    except Exception:
        pass
    _best_effort_background(background, snapshot_catalog, merchant_id)

    # Pricing recommendations
    gen_recs = None
    try:
        from apps.backend.services.pricing_buffer import generate_pricing_recommendations as _gen  # type: ignore
        gen_recs = _gen
    except Exception:
        pass
    _best_effort_background(background, gen_recs, merchant_id)

    return JSONResponse(content={
        "ok": True,
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "message": "Installed. Canonical merchant identity locked. Automation queued.",
        "next": {
            "brand_status": f"/brand/status?merchant_id={merchant_id}",
            "pricing_latest": f"/pricing/recommendations/latest?merchant_id={merchant_id}",
        }
    })
