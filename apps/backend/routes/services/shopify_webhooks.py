import os
import base64
import hmac
import hashlib
from fastapi import APIRouter, Request, Header, HTTPException

from apps.backend.routes.services.supabase_admin import select_one
from apps.backend.routes.services.shopify_incremental_service import process_order_paid

router = APIRouter(prefix="/shopify", tags=["shopify"])

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")

def _verify(raw: bytes, hmac_header: str) -> bool:
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode(),
        raw,
        hashlib.sha256,
    ).digest()
    return hmac.compare_digest(
        base64.b64encode(digest).decode(),
        hmac_header or "",
    )

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

    merchant = select_one("merchants", {"shop_domain": x_shopify_shop_domain})
    if not merchant or merchant.get("engine_state") != "ready":
        return {"ok": True, "ignored": True}

    if x_shopify_topic.lower() == "orders/paid":
        payload = await request.json()
        return process_order_paid(
            merchant_id=merchant["id"],
            points_per_dollar=float(merchant.get("points_per_dollar", 1.0)),
            order=payload,
        )

    return {"ok": True}
