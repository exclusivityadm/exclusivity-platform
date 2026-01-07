# apps/backend/routes/shopify.py
# =====================================================
# Exclusivity Backend — Shopify Routes (Webhooks)
#
# Mounted at: /shopify (prefix owned by main.py)
#
# Webhooks (HMAC-verified):
#   POST /shopify/webhooks/orders/create
#   POST /shopify/webhooks/orders/updated
#   POST /shopify/webhooks/customers/create
#   POST /shopify/webhooks/app/uninstalled
#
# Notes:
# - We store raw payloads safely in Supabase using service_role
# - We resolve merchant_id by merchants.shop_domain
# - We never expose tokens; uninstall clears tokens
# =====================================================

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional, Tuple

import requests
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["shopify"])  # prefix owned by main.py


# -----------------------------------------------------
# Helpers: Shopify HMAC verification
# -----------------------------------------------------

def _must_env(name: str) -> str:
    v = (os.getenv(name) or "").strip()
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def verify_shopify_hmac(raw_body: bytes, hmac_header: str, secret: str) -> bool:
    """
    Shopify sends base64(hmac_sha256(body, secret)) in X-Shopify-Hmac-Sha256
    """
    if not hmac_header:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)


def _shop_domain_from_headers(request: Request) -> str:
    # Shopify standard
    shop = (request.headers.get("X-Shopify-Shop-Domain") or "").strip().lower()
    if not shop:
        # Sometimes proxied integrations send Host; fallback (best-effort)
        shop = (request.headers.get("host") or "").strip().lower()
    return shop


# -----------------------------------------------------
# Helpers: Supabase service_role client (self-contained)
# -----------------------------------------------------

def _supabase_headers() -> Dict[str, str]:
    key = _must_env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _supabase_url(path: str) -> str:
    base = _must_env("SUPABASE_URL").rstrip("/")
    return f"{base}{path}"


def sb_select_one(table: str, filters: Dict[str, Any], columns: str = "*") -> Optional[Dict[str, Any]]:
    """
    Select a single row from PostgREST. Returns dict or None.
    """
    # PostgREST filter format: ?col=eq.value
    qs = "&".join([f"{k}=eq.{requests.utils.quote(str(v))}" for k, v in filters.items()])
    url = _supabase_url(f"/rest/v1/{table}?select={requests.utils.quote(columns)}&{qs}&limit=1")
    r = requests.get(url, headers=_supabase_headers(), timeout=20)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase select error ({table}): {r.text}")
    rows = r.json()
    return rows[0] if rows else None


def sb_upsert(table: str, row: Dict[str, Any], on_conflict: str) -> Dict[str, Any]:
    """
    Upsert via PostgREST.
    """
    url = _supabase_url(f"/rest/v1/{table}?on_conflict={requests.utils.quote(on_conflict)}")
    headers = _supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    r = requests.post(url, headers=headers, data=json.dumps(row), timeout=20)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase upsert error ({table}): {r.text}")
    out = r.json()
    return out[0] if isinstance(out, list) and out else (out if isinstance(out, dict) else {"ok": True})


def sb_delete(table: str, filters: Dict[str, Any]) -> None:
    qs = "&".join([f"{k}=eq.{requests.utils.quote(str(v))}" for k, v in filters.items()])
    url = _supabase_url(f"/rest/v1/{table}?{qs}")
    r = requests.delete(url, headers=_supabase_headers(), timeout=20)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase delete error ({table}): {r.text}")


# -----------------------------------------------------
# Canonical resolver: shop_domain -> merchant_id
# -----------------------------------------------------

def resolve_merchant_id(shop_domain: str) -> Optional[str]:
    shop_domain = (shop_domain or "").strip().lower()
    if not shop_domain:
        return None
    m = sb_select_one(
        "merchants",
        {"shop_domain": shop_domain},
        columns="merchant_id,shop_domain",
    )
    return (m or {}).get("merchant_id")


# -----------------------------------------------------
# Canonical persistence: orders/customers
# -----------------------------------------------------

def persist_order(merchant_id: str, shop_domain: str, payload: Dict[str, Any]) -> None:
    order_id = payload.get("id")
    if not order_id:
        return

    row = {
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "order_id": str(order_id),
        "payload": payload,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    # Assumption: table has unique on (merchant_id, order_id) OR just order_id.
    # We'll use composite if present; otherwise still safe if order_id unique.
    sb_upsert("shopify_orders", row, on_conflict="merchant_id,order_id")


def persist_customer(merchant_id: str, shop_domain: str, payload: Dict[str, Any]) -> None:
    customer_id = payload.get("id")
    if not customer_id:
        return

    row = {
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "customer_id": str(customer_id),
        "email": (payload.get("email") or "").strip().lower() or None,
        "payload": payload,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    sb_upsert("shopify_customers", row, on_conflict="merchant_id,customer_id")


# -----------------------------------------------------
# Webhook endpoint core
# -----------------------------------------------------

async def _handle_webhook(request: Request) -> Tuple[str, Dict[str, Any]]:
    raw = await request.body()
    secret = _must_env("SHOPIFY_API_SECRET")
    hmac_header = (request.headers.get("X-Shopify-Hmac-Sha256") or "").strip()

    tolerate_missing = (os.getenv("SHOPIFY_WEBHOOK_TOLERATE_MISSING_HMAC", "false") or "").lower() == "true"
    if not hmac_header and not tolerate_missing:
        raise HTTPException(401, "Missing Shopify HMAC header")

    if hmac_header and not verify_shopify_hmac(raw, hmac_header, secret):
        raise HTTPException(401, "Invalid Shopify HMAC")

    shop_domain = _shop_domain_from_headers(request)
    if not shop_domain:
        raise HTTPException(400, "Missing shop domain header")

    try:
        payload = json.loads(raw.decode("utf-8") if raw else "{}")
    except Exception:
        payload = {}

    return shop_domain, payload


# -----------------------------------------------------
# Routes
# -----------------------------------------------------

@router.get("/ping")
def ping():
    return {"ok": True, "service": "shopify"}


@router.post("/webhooks/orders/create")
async def webhook_orders_create(request: Request):
    shop_domain, payload = await _handle_webhook(request)
    merchant_id = resolve_merchant_id(shop_domain)
    if not merchant_id:
        # Accept (200) so Shopify stops retry storms, but tell logs what's wrong
        return {"ok": True, "ignored": True, "reason": "merchant_not_resolved", "shop_domain": shop_domain}

    persist_order(merchant_id, shop_domain, payload)
    return {"ok": True}


@router.post("/webhooks/orders/updated")
async def webhook_orders_updated(request: Request):
    shop_domain, payload = await _handle_webhook(request)
    merchant_id = resolve_merchant_id(shop_domain)
    if not merchant_id:
        return {"ok": True, "ignored": True, "reason": "merchant_not_resolved", "shop_domain": shop_domain}

    persist_order(merchant_id, shop_domain, payload)
    return {"ok": True}


@router.post("/webhooks/customers/create")
async def webhook_customers_create(request: Request):
    shop_domain, payload = await _handle_webhook(request)
    merchant_id = resolve_merchant_id(shop_domain)
    if not merchant_id:
        return {"ok": True, "ignored": True, "reason": "merchant_not_resolved", "shop_domain": shop_domain}

    persist_customer(merchant_id, shop_domain, payload)
    return {"ok": True}


@router.post("/webhooks/app/uninstalled")
async def webhook_app_uninstalled(request: Request):
    shop_domain, payload = await _handle_webhook(request)
    # merchant might not resolve after uninstall; we still clear tokens by shop_domain
    try:
        sb_delete("shopify_tokens", {"shop_domain": shop_domain})
    except Exception:
        # don't fail webhook; Shopify will retry aggressively
        pass
    return {"ok": True, "shop_domain": shop_domain}
