# apps/backend/services/supabase_admin_client.py
# =====================================================
# Minimal Supabase Admin Client (Service Role)
# - Used for OAuth binding + token storage without relying on other helpers
# =====================================================

from __future__ import annotations

import os
import requests
from typing import Any, Dict, Optional, Tuple


class SupabaseAdminClient:
    def __init__(self):
        self.url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
        self.key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        if not self.url or not self.key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

        self.rest = f"{self.url}/rest/v1"

    def _headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        h = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        if prefer:
            h["Prefer"] = prefer
        return h

    def select_one(self, table: str, filters: Dict[str, Any], columns: str = "*") -> Optional[Dict[str, Any]]:
        params = {"select": columns}
        for k, v in (filters or {}).items():
            params[k] = f"eq.{v}"

        r = requests.get(f"{self.rest}/{table}", headers=self._headers(), params=params, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"Supabase select_one error: {r.status_code} {r.text}")

        rows = r.json() or []
        return rows[0] if rows else None

    def upsert(self, table: str, payload: Dict[str, Any], on_conflict: str) -> Dict[str, Any]:
        # Prefer: resolution=merge-duplicates allows upsert
        headers = self._headers(prefer="return=representation,resolution=merge-duplicates")
        params = {"on_conflict": on_conflict}

        r = requests.post(f"{self.rest}/{table}", headers=headers, params=params, json=payload, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"Supabase upsert error: {r.status_code} {r.text}")

        rows = r.json() or []
        return rows[0] if rows else payload

    def insert(self, table: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = self._headers(prefer="return=representation")
        r = requests.post(f"{self.rest}/{table}", headers=headers, json=payload, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"Supabase insert error: {r.status_code} {r.text}")
        rows = r.json() or []
        return rows[0] if rows else payload
