import os
import hmac
import hashlib
import secrets
import urllib.parse
import requests
from typing import Dict, Optional

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")
SHOPIFY_SCOPES = os.getenv("SHOPIFY_SCOPES", "read_orders,read_customers")
SHOPIFY_REDIRECT_URI = os.getenv("SHOPIFY_REDIRECT_URI", "")  # e.g. https://<render-backend>/shopify/callback

class ShopifyOAuthError(Exception):
    pass

def _require_env():
    if not SHOPIFY_API_KEY or not SHOPIFY_API_SECRET or not SHOPIFY_REDIRECT_URI:
        raise ShopifyOAuthError(
            "Missing Shopify env. Require SHOPIFY_API_KEY, SHOPIFY_API_SECRET, SHOPIFY_REDIRECT_URI."
        )

def build_install_url(shop: str, state: str) -> str:
    _require_env()
    base = f"https://{shop}/admin/oauth/authorize"
    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": SHOPIFY_SCOPES,
        "redirect_uri": SHOPIFY_REDIRECT_URI,
        "state": state,
    }
    return base + "?" + urllib.parse.urlencode(params)

def verify_hmac(query_params: Dict[str, str]) -> bool:
    """
    Verify Shopify HMAC on callback query string.
    """
    _require_env()
    received_hmac = query_params.get("hmac", "")
    if not received_hmac:
        return False

    message_pairs = []
    for k in sorted(query_params.keys()):
        if k in ("hmac", "signature"):
            continue
        message_pairs.append(f"{k}={query_params[k]}")
    message = "&".join(message_pairs)

    digest = hmac.new(
        SHOPIFY_API_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(digest, received_hmac)

def exchange_code_for_token(shop: str, code: str) -> str:
    _require_env()
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_API_KEY,
        "client_secret": SHOPIFY_API_SECRET,
        "code": code,
    }
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code != 200:
        raise ShopifyOAuthError(f"Token exchange failed: {r.status_code} {r.text}")
    data = r.json()
    token = data.get("access_token")
    if not token:
        raise ShopifyOAuthError("Token exchange succeeded but access_token missing.")
    return token

def new_state() -> str:
    return secrets.token_urlsafe(24)
