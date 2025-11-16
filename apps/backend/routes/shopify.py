# apps/backend/routes/shopify.py
# ============================================================
# Shopify Embedded App Router (OAuth + Webhooks + Smoke Test)
# Now accrues points on orders/paid.
# ============================================================

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import os, hmac, hashlib, base64, time, json, requests

from apps.backend.db import get_supabase
from apps.backend.services.points import award_points

router = APIRouter()

# ---------- Env ----------
SHOPIFY_API_KEY        = os.getenv("SHOPIFY_API_KEY", "").strip()
SHOPIFY_API_SECRET     = os.getenv("SHOPIFY_API_SECRET", "").strip()
SHOPIFY_SCOPES         = os.getenv("SHOPIFY_SCOPES", "read_products,read_customers,read_orders,write_customers").strip()
APP_URL                = (os.getenv("SHOPIFY_APP_URL", "") or os.getenv("RENDER_EXTERNAL_URL", "")).strip().rstrip("/")
SHOPIFY_WEBHOOK_SECRET = (os.getenv("SHOPIFY_WEBHOOK_SECRET", "") or SHOPIFY_API_SECRET).strip()
FRONTEND_URL           = os.getenv("FRONTEND_URL", "").strip()
POINTS_DEFAULT         = float(os.getenv("POINTS_PER_USD_DEFAULT", "1"))

API_VERSION = "2024-07"  # adjust as needed

# ---------- Helpers ----------
def _require_env():
    if not (SHOPIFY_API_KEY and SHOPIFY_API_SECRET):
        raise HTTPException(500, "Shopify env not configured: missing SHOPIFY_API_KEY/SHOPIFY_API_SECRET")
    if not APP_URL:
        raise HTTPException(500, "Shopify env not configured: missing SHOPIFY_APP_URL (or RENDER_EXTERNAL_URL)")

def _normalize_shop(shop: str) -> str:
    s = (shop or "").strip().lower()
    if not s:
        raise HTTPException(400, "Missing shop")
    if not s.endswith(".myshopify.com"):
        s += ".myshopify.com"
    return s

def _make_state(merchant_id: Optional[str]) -> str:
    obj = {"ts": int(time.time())}
    if merchant_id:
        obj["merchant_id"] = merchant_id
    return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode()

def _parse_state(state: str) -> Dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(state.encode()).decode()
        return json.loads(raw)
    except Exception:
        return {}

def _verify_hmac_from_query(params: Dict[str, str]) -> bool:
    if "hmac" not in params:
        return False
    hmac_recv = params["hmac"]
    items = [(k, v) for k, v in params.items() if k != "hmac"]
    items.sort(key=lambda x: x[0])
    msg = "&".join([f"{k}={v}" for k, v in items])
    digest = hmac.new(SHOPIFY_API_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, hmac_recv)

def _verify_webhook_hmac(raw_body: bytes, header_hmac_b64: str) -> bool:
    digest = hmac.new(SHOPIFY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).digest()
    calc = base64.b64encode(digest).decode()
    return hmac.compare_digest(calc, header_hmac_b64 or "")

def _ensure_webhook(shop: str, access_token: str, topic: str, address: str):
    url = f"https://{shop}/admin/api/{API_VERSION}/webhooks.json"
    headers = {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            existing = r.json().get("webhooks", []) or []
            for w in existing:
                if w.get("address") == address and w.get("topic") == topic:
                    return
        payload = {"webhook": {"topic": topic, "address": address, "format": "json"}}
        requests.post(url, headers=headers, json=payload, timeout=30)
    except Exception:
        pass

def _save_shop_token(shop: str, token: str, scope: str, merchant_id: Optional[str] = None):
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")
    row = {"shop": shop, "access_token": token, "scope": scope}
    if merchant_id:
        row["merchant_id"] = merchant_id
    sb.table("shopify_shops").upsert(row, on_conflict="shop").execute()

def _get_shop_row(shop: str) -> Optional[dict]:
    sb = get_supabase()
    if not sb:
        return None
    data = sb.table("shopify_shops").select("*").eq("shop", shop).limit(1).execute().data
    return data[0] if data else None

def _points_per_usd(merchant_id: Optional[str]) -> float:
    if not merchant_id:
        return POINTS_DEFAULT
    sb = get_supabase()
    if not sb:
        return POINTS_DEFAULT
    row = sb.table("brand_settings").select("points_per_usd").eq("merchant_id", merchant_id).limit(1).execute().data
    if row and row[0].get("points_per_usd") is not None:
        try:
            return float(row[0]["points_per_usd"])
        except Exception:
            return POINTS_DEFAULT
    return POINTS_DEFAULT

# ---------- Routes ----------
@router.get("/install")
def install(shop: str, merchant_id: Optional[str] = None):
    _require_env()
    shop_norm = _normalize_shop(shop)
    state = _make_state(merchant_id)
    redirect_uri = f"{APP_URL}/shopify/callback"
    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": SHOPIFY_SCOPES,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    url = f"https://{shop_norm}/admin/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url)

@router.get("/callback")
def callback(request: Request):
    _require_env()
    q = dict(request.query_params)
    if not _verify_hmac_from_query(q):
        raise HTTPException(400, "Invalid HMAC")
    shop = _normalize_shop(q.get("shop", ""))
    code = q.get("code", "")
    state = q.get("state", "")

    if not code:
        raise HTTPException(400, "Missing code")

    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {"client_id": SHOPIFY_API_KEY, "client_secret": SHOPIFY_API_SECRET, "code": code}
    r = requests.post(token_url, json=payload, timeout=30)
    if r.status_code != 200:
        raise HTTPException(400, f"Token exchange failed: {r.text}")
    data = r.json()
    access_token = data.get("access_token")
    scope = data.get("scope", "")

    if not access_token:
        raise HTTPException(400, "No access_token in response")

    mid = _parse_state(state).get("merchant_id")
    _save_shop_token(shop, access_token, scope, merchant_id=mid)

    try:
        _ensure_webhook(shop, access_token, "customers/create", f"{APP_URL}/shopify/webhooks")
        _ensure_webhook(shop, access_token, "orders/paid",     f"{APP_URL}/shopify/webhooks")
    except Exception:
        pass

    if os.getenv("FRONTEND_URL", "").strip():
        return RedirectResponse(os.getenv("FRONTEND_URL"))
    return JSONResponse({"ok": True, "shop": shop, "scope": scope})

@router.post("/webhooks")
async def webhooks(request: Request):
    raw = await request.body()
    header_hmac = request.headers.get("X-Shopify-Hmac-Sha256", "")
    if not _verify_webhook_hmac(raw, header_hmac):
        raise HTTPException(401, "Invalid webhook signature")

    topic = request.headers.get("X-Shopify-Topic", "")
    shop  = _normalize_shop(request.headers.get("X-Shopify-Shop-Domain", ""))

    payload: Dict[str, Any] = {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        pass

    sb = get_supabase()
    if not sb:
        return JSONResponse({"ok": False, "error": "Supabase not configured"}, status_code=501)

    shop_row = _get_shop_row(shop)
    merchant_id = shop_row.get("merchant_id") if shop_row else None

    if topic == "customers/create":
        try:
            if merchant_id:
                cid = str(payload.get("id"))
                email = payload.get("email")
                sb.table("customers").upsert({
                    "merchant_id": merchant_id,
                    "customer_id": cid,
                    "email": email
                }, on_conflict="merchant_id,customer_id").execute()
        except Exception:
            pass

    if topic == "orders/paid":
        # Derive points = round(total_price * points_per_usd)
        try:
            if merchant_id:
                # Shopify money fields are strings; use total_price (store currency)
                total_price_str = payload.get("total_price") or "0"
                try:
                    total_price = float(total_price_str)
                except Exception:
                    total_price = 0.0

                ppu = _points_per_usd(merchant_id)
                delta = int(round(total_price * ppu))

                # Choose a customer id: the order has customer/id
                customer = payload.get("customer") or {}
                customer_id = str(customer.get("id") or payload.get("customer_id") or "unknown")

                award_points(
                    merchant_id=merchant_id,
                    customer_id=customer_id,
                    delta=delta,
                    reason="orders.paid",
                    metadata={"shop": shop, "order_id": payload.get("id"), "total_price": total_price, "ppu": ppu}
                )
        except Exception:
            # Swallow to avoid retries storm; you can log/monitor outside.
            pass

    return JSONResponse({"ok": True, "topic": topic})

@router.get("/test")
def test(shop: str):
    shop_norm = _normalize_shop(shop)
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")
    data = sb.table("shopify_shops").select("*").eq("shop", shop_norm).limit(1).execute().data
    if not data:
        raise HTTPException(404, "Shop not installed")
    token = data[0]["access_token"]
    url = f"https://{shop_norm}/admin/api/{API_VERSION}/shop.json"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token}, timeout=30)
    if r.status_code != 200:
        raise HTTPException(400, r.text)
    return r.json()
