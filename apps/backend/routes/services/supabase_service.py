# apps/backend/routes/services/supabase_service.py
# =====================================================
# Supabase service-role client (HTTP) — used for sensitive writes
# NOTE: This file is standalone to avoid touching your existing
#       supabase_admin helper; it is a canonical write layer for Drop B.
# =====================================================

from __future__ import annotations

import os
import requests
from typing import Any, Dict, Optional


class SupabaseServiceError(Exception):
    pass


def _base() -> str:
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    if not url:
        raise SupabaseServiceError("Missing SUPABASE_URL")
    return url


def _key() -> str:
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not key:
        raise SupabaseServiceError("Missing SUPABASE_SERVICE_ROLE_KEY")
    return key


def _headers() -> Dict[str, str]:
    key = _key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": "return=representation",
    }


def upsert(table: str, payload: Dict[str, Any], on_conflict: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_base()}/rest/v1/{table}"
    params = {}
    if on_conflict:
        params["on_conflict"] = on_conflict
    r = requests.post(url, headers=_headers(), params=params, json=payload, timeout=30)
    if r.status_code >= 300:
        raise SupabaseServiceError(f"Supabase upsert failed: {r.status_code} {r.text}")
    data = r.json()
    # Supabase returns list for inserts/upserts with return=representation
    return data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})


def select_one(table: str, filters: Dict[str, Any], columns: str = "*") -> Optional[Dict[str, Any]]:
    url = f"{_base()}/rest/v1/{table}"
    params = {"select": columns, "limit": "1"}
    for k, v in (filters or {}).items():
        params[k] = f"eq.{v}"
    r = requests.get(url, headers=_headers(), params=params, timeout=30)
    if r.status_code >= 300:
        raise SupabaseServiceError(f"Supabase select_one failed: {r.status_code} {r.text}")
    rows = r.json()
    return rows[0] if rows else None
