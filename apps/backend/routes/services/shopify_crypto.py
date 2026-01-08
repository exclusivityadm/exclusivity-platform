# apps/backend/routes/services/shopify_crypto.py
# =====================================================
# Shopify security helpers: HMAC verification + safe shop parsing
# =====================================================

from __future__ import annotations

import hmac
import hashlib
import base64
import urllib.parse
from typing import Dict, Any, Optional


def normalize_shop(shop: str) -> str:
    s = (shop or "").strip().lower()
    s = s.replace("https://", "").replace("http://", "").strip("/")
    return s


def verify_hmac(query_params: Dict[str, Any], api_secret: str) -> bool:
    """
    Verify Shopify OAuth callback query HMAC.
    Shopify requires:
      - remove "hmac" and "signature"
      - build message as sorted query string
      - compare computed HMAC-SHA256 hex digest to provided "hmac"
    """
    if not api_secret:
        return False

    provided = (query_params.get("hmac") or "").strip()
    if not provided:
        return False

    cleaned = {}
    for k, v in query_params.items():
        if k in ("hmac", "signature"):
            continue
        if v is None:
            continue
        cleaned[k] = v

    # Shopify uses '&' joined, keys sorted, values URL encoded
    message = urllib.parse.urlencode(sorted(cleaned.items()), doseq=True)

    digest = hmac.new(
        api_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(digest, provided)


def build_state(shop: str, nonce: str) -> str:
    raw = f"{normalize_shop(shop)}|{nonce}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").strip("=")


def parse_state(state: str) -> Optional[Dict[str, str]]:
    try:
        padded = state + "=" * (-len(state) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        shop, nonce = raw.split("|", 1)
        return {"shop": shop, "nonce": nonce}
    except Exception:
        return None
