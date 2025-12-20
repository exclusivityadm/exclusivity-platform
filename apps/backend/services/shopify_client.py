# apps/backend/services/shopify_client.py

from __future__ import annotations

import requests
from typing import Dict, Any, Optional
import time


class ShopifyClient:
    """
    Canonical Shopify REST client for Exclusivity.

    Design goals:
    - Simple, explicit REST usage (no magic SDKs)
    - Safe defaults
    - Deterministic behavior
    - Centralized rate-limit handling
    - Shopify-version pinned
    """

    API_VERSION = "2024-04"
    TIMEOUT_SECONDS = 20
    MAX_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 1.5

    def __init__(self, shop_domain: str, access_token: str):
        if not shop_domain or not access_token:
            raise ValueError("ShopifyClient requires shop_domain and access_token")

        self.shop_domain = shop_domain.lower().strip()
        self.access_token = access_token.strip()
        self.base_url = f"https://{self.shop_domain}/admin/api/{self.API_VERSION}"

        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ---------------------------------------------------------
    # Low-level request handler
    # ---------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> tuple[Dict[str, Any], Dict[str, str]]:
        """
        Performs a REST request with retry + rate-limit awareness.
        Returns (json_payload, response_headers).
        """
        url = f"{self.base_url}{path}"

        last_error: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json,
                    timeout=self.TIMEOUT_SECONDS,
                )

                # Shopify rate-limit handling (REST)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    sleep_for = float(retry_after) if retry_after else self.RETRY_BACKOFF_SECONDS
                    time.sleep(sleep_for)
                    continue

                response.raise_for_status()

                if response.content:
                    return response.json(), dict(response.headers)

                return {}, dict(response.headers)

            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_BACKOFF_SECONDS * attempt)
                    continue
                break

        raise RuntimeError(f"Shopify API request failed after retries: {last_error}")

    # ---------------------------------------------------------
    # Public REST helpers
    # ---------------------------------------------------------
    def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> tuple[Dict[str, Any], Dict[str, str]]:
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
    ) -> tuple[Dict[str, Any], Dict[str, str]]:
        return self._request("POST", path, json=json)

    def put(
        self,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
    ) -> tuple[Dict[str, Any], Dict[str, str]]:
        return self._request("PUT", path, json=json)

    def delete(
        self,
        path: str,
    ) -> tuple[Dict[str, Any], Dict[str, str]]:
        return self._request("DELETE", path)
