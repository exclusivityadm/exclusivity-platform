# apps/backend/services/shopify/hmac.py
# =====================================================
# Shopify HMAC verification helpers
# =====================================================

from __future__ import annotations

import hashlib
import hmac as hmaclib
from urllib.parse import urlencode
from typing import Dict, Any, Optional


def _to_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def verify_shopify_hmac(query: Dict[str, Any], api_secret: str) -> bool:
    """
    Verifies Shopify HMAC for OAuth callback.
    Shopify signs ALL query params except 'hmac' and 'signature' (legacy).
    """
    provided = _to_str(query.get("hmac"))
    if not provided:
        return False

    # Build message: sorted params excluding hmac/signature
    items = []
    for k in sorted(query.keys()):
        if k in ("hmac", "signature"):
            continue
        items.append((k, _to_str(query.get(k))))

    message = urlencode(items)
    digest = hmaclib.new(api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmaclib.compare_digest(digest, provided)
