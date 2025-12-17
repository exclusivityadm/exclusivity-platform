# FULL FILE — new
import os, hmac, hashlib, base64, requests

def verify_webhook(raw: bytes, sig: str | None) -> bool:
    secret = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
    digest = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(digest, sig or "")

def register_webhook(shop: str, token: str, topic: str, callback_path: str):
    url = f"https://{shop}/admin/api/2024-10/webhooks.json"
    base = os.getenv("BACKEND_PUBLIC_URL", "").rstrip("/")
    address = f"{base}{callback_path}"
    payload = {"webhook": {"topic": topic, "address": address, "format": "json"}}
    r = requests.post(url, json=payload, headers={"X-Shopify-Access-Token": token}, timeout=15)
    r.raise_for_status()

def map_order_to_points(order: dict) -> int:
    try:
        subtotal = float(order.get("subtotal_price", 0) or 0)
        return int(round(subtotal))
    except Exception:
        return 0

def extract_customer_id(order: dict) -> str:
    cust = order.get("customer") or {}
    return str(cust.get("id") or order.get("email") or "unknown")
