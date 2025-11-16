from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional, Dict, Any
from urllib.parse import urlencode, quote
import os, hmac, hashlib, base64, time, json, requests

# Env
SHOPIFY_API_KEY        = os.getenv("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET     = os.getenv("SHOPIFY_API_SECRET", "")
SHOPIFY_SCOPES         = os.getenv("SHOPIFY_SCOPES", "read_products,read_customers,read_orders,write_customers")
APP_URL                = os.getenv("SHOPIFY_APP_URL", "").rstrip("/")
SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", SHOPIFY_API_SECRET)

if not APP_URL:
    # Fallback to Render's public URL if provided via RENDER_EXTERNAL_URL
    APP_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")

# Optional: link install to a merchant via ?merchant_id=... (stored in state)
def _make_state(merchant_id: Optional[str]) -> str:
    data = {"ts": int(time.time())}
    if merchant_id:
        data["merchant_id"] = merchant_id
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

def _parse_state(state: str) -> Dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(state.encode()).decode()
        return json.loads(raw)
    except Exception:
        return {}

def _verify_hmac_from_query(params: Dict[str, str]) -> bool:
    """Verify Shopify HMAC on callback query using API secret."""
    if "hmac" not in params: return False
    hmac_recv = params["hmac"]
    items = [(k, v) for k, v in params.items() if k != "hmac"]
    items.sort(key=lambda x: x[0])
    msg = "&".join([f"{k}={v}" for k, v in items])
    digest = hmac.new(SHOPIFY_API_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, hmac_recv)

def _verify_webhook_hmac(raw_body: bytes, header_hmac_b64: str) -> bool:
    digest = hmac.new(SHOPIFY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).digest()
    calc = base64.b64encode(digest).decode()
    return hmac.compare_digest(calc, header_hmac_b64)

# Supabase client
from apps.backend.db import get_supabase

router = APIRouter()

@router.get("/install")
def install(shop: str, merchant_id: Optional[str] = None):
    """Start OAuth flow. Example: /shopify/install?shop=mybrand.myshopify.com"""
    if not (SHOPIFY_API_KEY and SHOPIFY_API_SECRET and APP_URL):
        raise HTTPException(500, "Shopify env not configured")
    if not shop.endswith(".myshopify.com"):
        shop += ".myshopify.com"
    state = _make_state(merchant_id)
    redirect_uri = f"{APP_URL}/shopify/callback"
    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": SHOPIFY_SCOPES,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    url = f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url)

@router.get("/callback")
def callback(request: Request):
    """OAuth callback from Shopify."""
    q = dict(request.query_params)
    if not _verify_hmac_from_query(q):
        raise HTTPException(400, "Invalid HMAC")
    shop = q.get("shop", "")
    code = q.get("code", "")
    state = q.get("state", "")
    if not (shop and code):
        raise HTTPException(400, "Missing shop/code")

    # Exchange code for token
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {"client_id": SHOPIFY_API_KEY, "client_secret": SHOPIFY_API_SECRET, "code": code}
    r = requests.post(token_url, json=payload, timeout=30)
    if r.status_code != 200:
        raise HTTPException(400, f"Token exchange failed: {r.text}")
    data = r.json()
    access_token = data.get("access_token")
    scope = data.get("scope", "")

    # Save to Supabase
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")
    mid = _parse_state(state).get("merchant_id")
    up = {"shop": shop, "access_token": access_token, "scope": scope}
    if mid: up["merchant_id"] = mid
    sb.table("shopify_shops").upsert(up, on_conflict="shop").execute()

    # Optional: register webhooks
    try:
        _ensure_webhook(shop, access_token, "orders/paid", f"{APP_URL}/shopify/webhooks")
        _ensure_webhook(shop, access_token, "customers/create", f"{APP_URL}/shopify/webhooks")
    except Exception:
        pass

    # Redirect to your frontend admin (optional)
    frontend = os.getenv("FRONTEND_URL", "")
    if frontend:
        return RedirectResponse(frontend)
    return JSONResponse({"ok": True, "shop": shop, "scope": scope})

def _ensure_webhook(shop: str, access_token: str, topic: str, address: str):
    url = f"https://{shop}/admin/api/2024-07/webhooks.json"
    headers = {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}
    # List existing
    r = requests.get(url, headers=headers, timeout=30)
    existing = r.json().get("webhooks", []) if r.status_code == 200 else []
    for w in existing:
        if w.get("address") == address and w.get("topic") == topic:
            return
    # Create
    payload = {"webhook": {"topic": topic, "address": address, "format": "json"}}
    requests.post(url, headers=headers, json=payload, timeout=30)

@router.post("/webhooks")
async def webhooks(request: Request):
    """Verify HMAC and handle topics like orders/paid, customers/create."""
    raw = await request.body()
    sig = request.headers.get("X-Shopify-Hmac-Sha256", "")
    if not _verify_webhook_hmac(raw, sig):
        raise HTTPException(401, "Invalid webhook signature")

    topic = request.headers.get("X-Shopify-Topic", "")
    shop  = request.headers.get("X-Shopify-Shop-Domain", "")
    payload = {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        pass

    # Minimal handlers — extend as needed
    sb = get_supabase()
    if sb and topic == "customers/create":
        # Ensure customer record exists (baseline mapping)
        cid = str(payload.get("id"))
        email = payload.get("email")
        # Try to link to merchant if installed
        shop_row = sb.table("shopify_shops").select("*").eq("shop", shop).limit(1).execute().data
        merchant_id = shop_row[0]["merchant_id"] if shop_row and shop_row[0].get("merchant_id") else None
        if merchant_id:
            # upsert into customers
            sb.table("customers").upsert({
                "merchant_id": merchant_id,
                "customer_id": cid,
                "email": email
            }, on_conflict="merchant_id,customer_id").execute()

    if sb and topic == "orders/paid":
        # Hook: you could award points per order here later
        pass

    return JSONResponse({"ok": True, "topic": topic})

@router.get("/test")
def test(shop: str):
    """Smoke test: fetch shop info using stored token."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")
    row = sb.table("shopify_shops").select("*").eq("shop", shop).limit(1).execute().data
    if not row:
        raise HTTPException(404, "Shop not installed")
    token = row[0]["access_token"]
    r = requests.get(f"https://{shop}/admin/api/2024-07/shop.json",
                     headers={"X-Shopify-Access-Token": token}, timeout=30)
    if r.status_code != 200:
        raise HTTPException(400, r.text)
    return r.json()
