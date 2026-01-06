import os
import time
import requests
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request

from apps.backend.routes.services.supabase_admin import insert_one, upsert_one, select_one, update_where, new_uuid

router = APIRouter(prefix="/shopify", tags=["shopify"])

SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "").rstrip("/")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

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

def _register_webhook(shop_domain: str, access_token: str, topic: str, address: str) -> Optional[int]:
    """
    Best-effort webhook registration. Returns webhook id if created.
    """
    url = _shopify_rest(shop_domain, access_token, "/webhooks.json")
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    payload = {"webhook": {"topic": topic, "address": address, "format": "json"}}
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code in (200, 201):
        return int(r.json()["webhook"]["id"])
    # If already exists or Shopify rejects due to duplicates, we do not fail install.
    return None

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

@router.get("/oauth/callback")
async def shopify_oauth_callback(request: Request):
    """
    Canonical: OAuth success = merchant UUID creation + webhook registration + backfill enqueue.
    No onboarding. No UI gating beyond engine_state.
    """
    _required_env()

    q = dict(request.query_params)
    shop_domain = (q.get("shop") or "").strip().lower()
    code = (q.get("code") or "").strip()

    if not shop_domain or not code:
        raise HTTPException(status_code=400, detail="missing_shop_or_code")

    access_token = _exchange_code_for_token(shop_domain, code)

    # Create or retrieve merchant by shop_domain (Exclusivity UUID is canonical)
    merchant = select_one("merchants", {"shop_domain": shop_domain})
    if not merchant:
        merchant_id = new_uuid()
        merchant = insert_one("merchants", {
            "id": merchant_id,
            "shop_domain": shop_domain,
            "engine_state": "hydrating",
            "shopify_access_token": access_token,
            "points_per_dollar": 1.0,
        })
    else:
        # Reinstall/refresh token: lock engine back to hydrating until backfill completes again (safe)
        update_where("merchants", {"id": merchant["id"]}, {
            "engine_state": "hydrating",
            "shopify_access_token": access_token,
        })

    # Register webhooks (mandatory engine continuity)
    webhook_address = f"{BACKEND_PUBLIC_URL}/shopify/webhook"
    wid_paid = _register_webhook(shop_domain, access_token, "orders/paid", webhook_address)
    wid_refunded = _register_webhook(shop_domain, access_token, "orders/refunded", webhook_address)

    # Persist webhook ids (best-effort metadata)
    try:
        upsert_one("shopify_webhook_registry", {
            "merchant_id": merchant["id"],
            "shop_domain": shop_domain,
            "orders_paid_webhook_id": wid_paid,
            "orders_refunded_webhook_id": wid_refunded,
            "updated_at": time.time(),
        }, conflict_cols="merchant_id")
    except Exception:
        # Table may not exist yet; we remain engine-correct without it.
        pass

    # Enqueue backfill job immediately (mandatory first action after install)
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

    # Return a simple acknowledgement (frontend can poll engine_state if needed later)
    return {
        "ok": True,
        "merchant_id": merchant["id"],
        "shop_domain": shop_domain,
        "engine_state": "hydrating",
        "webhooks": {
            "orders_paid": bool(wid_paid),
            "orders_refunded": bool(wid_refunded),
        },
        "backfill": "queued",
    }
