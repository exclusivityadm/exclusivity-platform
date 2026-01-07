# apps/backend/services/shopify/oauth.py
# =====================================================
# Shopify OAuth helpers: signed state + URL builders + token exchange
# =====================================================

from __future__ import annotations

import os
import time
import json
import base64
import hashlib
import hmac as hmaclib
import requests
from typing import Any, Dict, Optional, Tuple


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def _sign(payload_b64: str, secret: str) -> str:
    sig = hmaclib.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(sig)


def make_state(shop: str, secret: str, ttl_seconds: int = 900) -> str:
    """
    Signed compact state token: base64url(payload).base64url(sig)
    payload = { shop, iat, exp }
    """
    now = int(time.time())
    payload = {"shop": shop, "iat": now, "exp": now + int(ttl_seconds)}
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _sign(payload_b64, secret)
    return f"{payload_b64}.{sig}"


def verify_state(state: str, secret: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Returns (ok, payload, error)
    """
    try:
        if not state or "." not in state:
            return (False, None, "Missing/invalid state")

        payload_b64, sig = state.split(".", 1)
        expected = _sign(payload_b64, secret)
        if not hmaclib.compare_digest(expected, sig):
            return (False, None, "Invalid state signature")

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        now = int(time.time())
        if int(payload.get("exp", 0)) < now:
            return (False, None, "State expired")

        return (True, payload, "")
    except Exception as e:
        return (False, None, f"State verify error: {e}")


def normalize_shop(shop: str) -> str:
    s = (shop or "").strip().lower()
    s = s.replace("https://", "").replace("http://", "").split("/")[0]
    # Shopify shops are like foo.myshopify.com
    return s


def build_authorize_url(shop: str, api_key: str, scopes: str, redirect_uri: str, state: str) -> str:
    shop = normalize_shop(shop)
    base = f"https://{shop}/admin/oauth/authorize"
    params = {
        "client_id": api_key,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    # Keep it simple; Shopify accepts standard query encoding
    from urllib.parse import urlencode
    return f"{base}?{urlencode(params)}"


def exchange_code_for_token(shop: str, api_key: str, api_secret: str, code: str) -> str:
    shop = normalize_shop(shop)
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {"client_id": api_key, "client_secret": api_secret, "code": code}
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Shopify token exchange failed: {r.status_code} {r.text}")
    j = r.json() or {}
    token = j.get("access_token")
    if not token:
        raise RuntimeError("Shopify token exchange: missing access_token")
    return token
