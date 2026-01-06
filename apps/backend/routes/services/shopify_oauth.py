import os
import requests
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from apps.backend.routes.services.supabase_admin import insert_one, upsert_one, select_one, update_where, new_uuid

router = APIRouter(prefix="/shopify", tags=["shopify"])

SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "").rstrip("/")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "")

def _required_env() -> None:
    missing = []
    for k, v in {
        "BACKEND_PUBLIC_URL": BACKEND_PUBLIC_URL,
        "SHOPIFY_CLIENT_ID": SHOPIFY_CLIENT_ID,
        "SHOPIFY_CLIENT_SECRET": SHOPIFY_CLIENT_SECRET,
    }.items():
        if not v:
            missing.append(k)
    if missing:
        raise HTTPException(status_code=500, detail=f"Missing env: {','.join(missing)}")

def _shopify_rest(shop_domain: str, access_token: str, path: str) -> str:
    return f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/{path.lstrip('/')}"

def _exchange_code_for_token(shop_domain: str, code: str) -> str:
    url = f"https://{shop_domain}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
        "code": code,
    }
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code != 200:
        raise HTTPException(status_code=400, detail=f"oauth_exchange_failed: {r.text}")
    return r.json()["access_token"]

def _register_webhook(shop_domain: str, access_token: str, topic: str, address: str) -> Optional[int]:
    url = _shopify_rest(shop_domain, access_token, "/webhooks.json")
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    payload = {"webhook": {"topic": topic, "address": address, "format": "json"}}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code in (200, 201):
        return int(r.json()["webhook"]["id"])
    return None

@router.get("/oauth/callback")
async def shopify_oauth_callback(request: Request):
    _required_env()
    q = dict(request.query_params)
    shop_domain = (q.get("shop") or "").strip().lower()
    code = (q.get("code") or "").strip()
    if not shop_domain or not code:
        raise HTTPException(status_code=400, detail="missing_shop_or_code")

    access_token = _exchange_code_for_token(shop_domain, code)

    merchant = select_one("merchants", {"shop_domain": shop_domain})
    if not merchant:
        merchant_id = new_uuid()
        merchant = insert_one("merchants", {
            "id": merchant_id,
            "shop_domain": shop_domain,
            "engine_state": "hydrating",
            "is_active": True,
            "shopify_access_token": access_token,
            "points_per_dollar": 1.0,
        })
    else:
        update_where("merchants", {"id": merchant["id"]}, {
            "engine_state": "hydrating",
            "is_active": True,
            "shopify_access_token": access_token,
        })

    webhook_address = f"{BACKEND_PUBLIC_URL}/shopify/webhook"
    created = {
        "orders_paid": bool(_register_webhook(shop_domain, access_token, "orders/paid", webhook_address)),
        "orders_refunded": bool(_register_webhook(shop_domain, access_token, "orders/refunded", webhook_address)),
        "orders_cancelled": bool(_register_webhook(shop_domain, access_token, "orders/cancelled", webhook_address)),
        "app_uninstalled": bool(_register_webhook(shop_domain, access_token, "app/uninstalled", webhook_address)),
    }

    # Enqueue backfill (mandatory)
    try:
        insert_one("shopify_backfill_jobs", {
            "merchant_id": merchant["id"],
            "shop_domain": shop_domain,
            "status": "queued",
        })
    except Exception:
        upsert_one("shopify_backfill_jobs", {
            "merchant_id": merchant["id"],
            "shop_domain": shop_domain,
            "status": "queued",
            "run_after": None,
            "error_last": None,
        }, conflict_cols="merchant_id")

    return {
        "ok": True,
        "merchant_id": merchant["id"],
        "shop_domain": shop_domain,
        "engine_state": "hydrating",
        "webhooks_registered": created,
        "backfill": "queued",
    }
