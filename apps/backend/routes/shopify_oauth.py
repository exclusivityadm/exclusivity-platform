# FULL FILE — new
import os, urllib.parse, hmac, hashlib, requests

def oauth_start(shop: str, state: str):
    params = {
        "client_id": os.getenv("SHOPIFY_API_KEY", ""),
        "scope": os.getenv("SHOPIFY_SCOPES", "read_customers,read_orders"),
        "redirect_uri": os.getenv("SHOPIFY_REDIRECT_URI", ""),
        "state": state,
    }
    return f"https://{shop}/admin/oauth/authorize?{urllib.parse.urlencode(params)}"

def verify_hmac(query: dict) -> bool:
    secret = os.getenv("SHOPIFY_API_SECRET", "")
    h = query.pop("hmac", "")
    message = "&".join([f"{k}={v}" for k, v in sorted(query.items())])
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, h)

def exchange_token(shop: str, code: str):
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": os.getenv("SHOPIFY_API_KEY", ""),
        "client_secret": os.getenv("SHOPIFY_API_SECRET", ""),
        "code": code
    }
    r = requests.post(url, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]
