from __future__ import annotations

import os
import time
import requests
from typing import Any, Dict, Optional, Tuple


SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-01")


class ShopifyClient:
    """
    Minimal Shopify Admin REST client with:
    - explicit shop domain
    - access token auth
    - basic retry for 429 rate limits
    """

    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain.strip()
        self.access_token = access_token.strip()

    def _base(self) -> str:
        return f"https://{self.shop_domain}/admin/api/{SHOPIFY_API_VERSION}"

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get(self, path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 20) -> Tuple[Dict[str, Any], Dict[str, str]]:
        url = self._base() + path
        for attempt in range(1, 5):
            r = requests.get(url, headers=self._headers(), params=params or {}, timeout=timeout)
            if r.status_code == 429:
                # naive retry, Shopify rate limit
                time.sleep(0.5 * attempt)
                continue
            r.raise_for_status()
            return (r.json() if r.text else {}, dict(r.headers))
        r.raise_for_status()
        return ({}, dict(r.headers))

    @staticmethod
    def parse_next_page_info(link_header: Optional[str]) -> Optional[str]:
        """
        Shopify uses cursor pagination with Link header. We store page_info as opaque cursor.
        Example: <https://shop/admin/api/2024-01/orders.json?limit=50&page_info=xxxxx>; rel="next"
        """
        if not link_header:
            return None
        parts = [p.strip() for p in link_header.split(",")]
        for p in parts:
            if 'rel="next"' in p:
                # extract page_info
                start = p.find("page_info=")
                if start == -1:
                    return None
                tail = p[start + len("page_info="):]
                end = tail.find(">")  # cursor ends before '>'
                cursor = tail[:end] if end != -1 else tail
                cursor = cursor.replace("&", "").strip()
                return cursor
        return None
