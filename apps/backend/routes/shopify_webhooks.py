import os
import base64
import hmac
import hashlib
from typing import Any, Dict

from fastapi import APIRouter, Request, Header, HTTPException

from apps.backend.routes.services.supabase_admin import select_one
from apps.backend.routes.services.shopify_incremental_service import process_order_paid, process_order_refunded

router = APIRouter(prefix="/shopify", tags=["shopify"])

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")

def _verify(raw: bytes, hmac_header: str) -> bool:
    if not SHOPIFY_WEBHOOK_SECRET:
        return False
    digest = hmac.new(SHOPIFY_WEBHOOK_SECRET.encode("utf-8"), raw, hashlib.sha256).digest()
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
    if not _verify(raw, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="invalid_signature")

    topic = (x_shopify_topic or "").strip().lower()
    shop_domain = (x_shopify_shop_domain or "").strip().lower()

    merchant = select_one("merchants", {"shop_domain": shop_domain})
    if not merchant:
        return {"ok": True, "ignored": True, "reason": "merchant_not_found"}

    if merchant.get("engine_state") != "ready":
        # accept to stop Shopify retry storms; do not mutate before engine is ready
        return {"ok": True, "ignored": True, "reason": "engine_not_ready"}

    payload: Dict[str, Any] = await request.json()

    if topic == "orders/paid":
        return process_order_paid(
            merchant_id=merchant["id"],
            points_per_dollar=float(merchant.get("points_per_dollar") or 1.0),
            order=payload,
        )

    if topic == "orders/refunded":
        return process_order_refunded(
            merchant_id=merchant["id"],
            points_per_dollar=float(merchant.get("points_per_dollar") or 1.0),
            order=payload,
        )

    return {"ok": True, "ignored": True, "reason": f"unhandled_topic:{topic}"}
