import os
import base64
import hmac
import hashlib
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException, Request

from apps.backend.lib.supabase_admin import select_one, upsert_one, insert_one, update_where
from apps.backend.services.shopify_incremental_service import process_order_paid

router = APIRouter(prefix="/shopify", tags=["shopify"])

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")

def _verify_shopify_webhook(raw_body: bytes, hmac_header: str) -> bool:
    if not SHOPIFY_WEBHOOK_SECRET:
        # If secret is missing, fail closed.
        return False
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).digest()
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header or "")

@router.post("/webhook")
async def shopify_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(default=""),
    x_shopify_topic: str = Header(default=""),
    x_shopify_shop_domain: str = Header(default=""),
):
    raw = await request.body()

    if not _verify_shopify_webhook(raw, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="invalid_webhook_signature")

    topic = (x_shopify_topic or "").strip().lower()
    shop_domain = (x_shopify_shop_domain or "").strip().lower()

    if not shop_domain:
        raise HTTPException(status_code=400, detail="missing_shop_domain")

    merchant = select_one("merchants", {"shop_domain": shop_domain})
    if not merchant:
        # If merchant isn't found, we accept but do nothing (prevents Shopify retries storm).
        return {"ok": True, "ignored": True, "reason": "merchant_not_found"}

    if merchant.get("engine_state") != "ready":
        # Engine not hydrated yet -> accept webhook but do not mutate state (avoid partial truth).
        return {"ok": True, "ignored": True, "reason": "engine_not_ready"}

    payload: Dict[str, Any] = await request.json()

    if topic == "orders/paid":
        points_per_dollar = float(merchant.get("points_per_dollar") or 1.0)
        out = process_order_paid(
            merchant_id=merchant["id"],
            points_per_dollar=points_per_dollar,
            order=payload,
        )
        return out

    # Unhandled topics are acknowledged without action
    return {"ok": True, "ignored": True, "reason": f"unhandled_topic:{topic}"}


@router.post("/backfill/run")
async def shopify_backfill_run(
    body: Dict[str, Any],
    x_admin_token: str = Header(default=""),
):
    """
    Canonical admin-only trigger: enqueues (or re-queues) a backfill job.
    This endpoint does NOT do long synchronous work.
    """
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

    merchant_id = body.get("merchant_id")
    shop_domain = (body.get("shop_domain") or "").strip().lower()
    access_token = body.get("access_token")
    points_per_dollar = float(body.get("points_per_dollar") or 1.0)

    if not merchant_id or not shop_domain or not access_token:
        raise HTTPException(status_code=400, detail="missing_fields")

    # Update merchant integration metadata + lock engine to hydrating
    update_where("merchants", {"id": merchant_id}, {
        "shop_domain": shop_domain,
        "shopify_access_token": access_token,
        "points_per_dollar": points_per_dollar,
        "engine_state": "hydrating",
    })

    # Enqueue job (idempotent)
    try:
        insert_one("shopify_backfill_jobs", {
            "merchant_id": merchant_id,
            "shop_domain": shop_domain,
            "status": "queued",
        })
    except Exception:
        # If exists, reset to queued
        upsert_one("shopify_backfill_jobs", {
            "merchant_id": merchant_id,
            "shop_domain": shop_domain,
            "status": "queued",
            "run_after": None,
            "error_last": None,
        }, conflict_cols="merchant_id")

    return {"ok": True, "queued": True, "merchant_id": merchant_id, "shop_domain": shop_domain}
