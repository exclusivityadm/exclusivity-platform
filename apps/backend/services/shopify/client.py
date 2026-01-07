# apps/backend/services/shopify/client.py
# =====================================================
# Shopify REST client using stored access token
# =====================================================

from __future__ import annotations

import requests
from typing import Any, Dict, Optional
from apps.backend.services.supabase_admin_client import SupabaseAdminClient


class ShopifyClient:
    def __init__(self, shop_domain: str, merchant_id: Optional[str] = None):
        self.shop = shop_domain.strip().lower()
        self.sb = SupabaseAdminClient()
        self.token = self._load_token(merchant_id)
        if not self.token:
            raise RuntimeError("Missing Shopify access token")

        self.base = f"https://{self.shop}/admin/api/2024-01"

    def _load_token(self, merchant_id: Optional[str]) -> Optional[str]:
        # Prefer shopify_tokens table
        try:
            row = None
            if merchant_id:
                row = self.sb.select_one("shopify_tokens", {"merchant_id": merchant_id}, columns="access_token")
            if not row:
                row = self.sb.select_one("shopify_tokens", {"shop_domain": self.shop}, columns="access_token")
            if row and row.get("access_token"):
                return row.get("access_token")
        except Exception:
            pass

        # Fallback: merchants.shopify_access_token
        m = self.sb.select_one("merchants", {"shop_domain": self.shop}, columns="shopify_access_token")
        return m.get("shopify_access_token") if m else None

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.token,
            "Content-Type": "application/json",
        }

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base}{path}"
        r = requests.get(url, headers=self._headers(), params=params or {}, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"Shopify GET {path} failed: {r.status_code} {r.text}")
        return r.json()
