# apps/backend/routes/shopify.py
# =====================================================
# Shopify Webhooks + Utilities (Day One)
#
# Mounted under /shopify by main.py
#
# POST /shopify/webhooks/app_uninstalled
# POST /shopify/webhooks/customers_create
# POST /shopify/webhooks/orders_create
#
# Notes:
# - Webhooks must be verified using X-Shopify-Hmac-Sha256 over raw body
# - This file includes canonical verification so we don't drift again
# =====================================================

from __future__ import annotations

import os
import hmac
import hashlib
import base64
from fastapi import APIRouter, Request, HTTPException
from typing import Any, Dict

from apps.backend.routes.services.shopify_crypto import normalize_shop
from apps.backend.routes.services.supabase_service import select_one, upsert, SupabaseServiceError

router = APIRouter(tags=["shopify"])  # prefix owned by main.py


def _secret() -> str:
    s = (os.getenv("SHOPIFY_API_SECRET") or "").strip()
    if not s:
        raise HTTPException(500, "Missing SHOPIFY_API_SECRET")
    return s


def verify_webhook_hmac(raw_body: bytes, hmac_header: str, api_secret: str) -> bool:
    """
    Shopify webhooks sign base64(HMAC-SHA256(raw_body, secret))
    header: X-Shopify-Hmac-Sha256
    """
    computed = base64.b64encode(
        hmac.new(api_secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    ).decode("utf-8")
    return hmac.compare_digest(computed, (hmac_header or "").strip())


async def _require_valid_webhook(request: Request) -> Dict[str, Any]:
    raw = await request.body()
    hdr = request.headers.get("X-Shopify-Hmac-Sha256", "")
    if not verify_webhook_hmac(raw, hdr, _secret()):
        raise HTTPException(401, "Invalid webhook HMAC")
    try:
        return await request.json()
    except Exception:
        return {}


@router.post("/webhooks/app_uninstalled")
async def webhook_app_uninstalled(request: Request):
    payload = await _require_valid_webhook(request)
    shop = normalize_shop(request.headers.get("X-Shopify-Shop-Domain", "") or payload.get("myshopify_domain", ""))
    if not shop:
        return {"ok": True}

    try:
        merchant = select_one("merchants", {"shop_domain": shop}, columns="merchant_id,shop_domain")
        if merchant and merchant.get("merchant_id"):
            mid = merchant["merchant_id"]
            # mark uninstalled, keep record (Day One auditability)
            upsert("merchants", {"merchant_id": mid, "shop_domain": shop, "installed": False}, on_conflict="shop_domain")
        return {"ok": True}
    except SupabaseServiceError:
        return {"ok": True}


@router.post("/webhooks/customers_create")
async def webhook_customers_create(request: Request):
    payload = await _require_valid_webhook(request)
    shop = normalize_shop(request.headers.get("X-Shopify-Shop-Domain", ""))
    if not shop:
        return {"ok": True}

    try:
        merchant = select_one("merchants", {"shop_domain": shop}, columns="merchant_id")
        if not merchant:
            return {"ok": True}
        mid = merchant["merchant_id"]
        cid = payload.get("id")
        if cid:
            upsert(
                "shopify_customers",
                {"merchant_id": mid, "shopify_customer_id": int(cid), "payload": payload},
                on_conflict="merchant_id,shopify_customer_id",
            )
        return {"ok": True}
    except Exception:
        return {"ok": True}


@router.post("/webhooks/orders_create")
async def webhook_orders_create(request: Request):
    payload = await _require_valid_webhook(request)
    shop = normalize_shop(request.headers.get("X-Shopify-Shop-Domain", ""))
    if not shop:
        return {"ok": True}

    try:
        merchant = select_one("merchants", {"shop_domain": shop}, columns="merchant_id")
        if not merchant:
            return {"ok": True}
        mid = merchant["merchant_id"]
        oid = payload.get("id")
        if oid:
            upsert(
                "shopify_orders",
                {"merchant_id": mid, "shopify_order_id": int(oid), "payload": payload},
                on_conflict="merchant_id,shopify_order_id",
            )
        return {"ok": True}
    except Exception:
        return {"ok": True}
