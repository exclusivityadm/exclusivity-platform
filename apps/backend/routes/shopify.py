# FULL FILE — new
from fastapi import APIRouter, HTTPException, Request
import json, uuid

try:
    from app.db import supabase
except Exception:
    supabase = None

from app.services.shopify_oauth import oauth_start, verify_hmac, exchange_token
from app.services.shopify_webhooks import verify_webhook, map_order_to_points, extract_customer_id

router = APIRouter(prefix="/shopify", tags=["shopify"])

@router.get("/oauth/start")
def start(shop: str):
    state = str(uuid.uuid4())
    return {"auth_url": oauth_start(shop, state), "state": state}

@router.get("/oauth/callback")
def callback(hmac: str, shop: str, code: str, state: str, **kwargs):
    if supabase is None:
        raise HTTPException(500, "Database client not configured")

    q = {"shop": shop, "code": code, "state": state, **kwargs, "hmac": hmac}
    if not verify_hmac(q):
        raise HTTPException(401, "invalid hmac")

    token = exchange_token(shop, code)

    bp = supabase.table("brand_profile").select("merchant_id").eq("store_domain", shop).limit(1).execute()
    if not getattr(bp, "data", None):
        raise HTTPException(400, "merchant not found for this shop domain")

    merchant_id = bp.data[0]["merchant_id"]

    supabase.table("shopify_install").upsert({
        "merchant_id": merchant_id,
        "shop_domain": shop,
        "access_token": token,
        "scope": ""
    }).execute()

    # Register webhooks
    try:
        from app.services.shopify_webhooks import register_webhook
        register_webhook(shop, token, "orders/paid", "/shopify/webhooks/orders-paid")
        register_webhook(shop, token, "customers/create", "/shopify/webhooks/customers-created")
    except Exception:
        pass

    return {"ok": True}

@router.post("/webhooks/orders-paid")
async def orders_paid(request: Request):
    if supabase is None:
        raise HTTPException(500, "Database client not configured")

    raw = await request.body()
    sig = request.headers.get("X-Shopify-Hmac-Sha256")
    if not verify_webhook(raw, sig):
        raise HTTPException(401, "bad sig")

    payload = json.loads(raw)
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")

    supabase.table("shopify_webhook_log").insert({
        "topic": "orders/paid",
        "shop_domain": shop_domain,
        "payload": payload
    }).execute()

    inst = supabase.table("shopify_install").select("merchant_id").eq("shop_domain", shop_domain).limit(1).execute()
    if getattr(inst, "data", None):
        merchant_id = inst.data[0]["merchant_id"]
        pts = map_order_to_points(payload)
        customer_id = extract_customer_id(payload)
        supabase.table("points_ledger").insert({
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "delta": pts,
            "reason": "order_paid",
            "ref": {"order_id": payload.get("id")}
        }).execute()
    return {"ok": True}

@router.post("/webhooks/customers-created")
async def customers_created(request: Request):
    if supabase is None:
        raise HTTPException(500, "Database client not configured")

    raw = await request.body()
    sig = request.headers.get("X-Shopify-Hmac-Sha256")
    if not verify_webhook(raw, sig):
        raise HTTPException(401, "bad sig")

    payload = json.loads(raw)
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")

    supabase.table("shopify_webhook_log").insert({
        "topic": "customers/create",
        "shop_domain": shop_domain,
        "payload": payload
    }).execute()

    return {"ok": True}
