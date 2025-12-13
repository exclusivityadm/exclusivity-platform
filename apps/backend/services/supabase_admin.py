import os
import uuid
import requests
from typing import Any, Dict, List, Optional

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

class SupabaseAdminError(Exception):
    pass

def _headers() -> Dict[str, str]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise SupabaseAdminError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend env.")
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _rest_url(table: str) -> str:
    if not SUPABASE_URL:
        raise SupabaseAdminError("Missing SUPABASE_URL in backend env.")
    return f"{SUPABASE_URL}/rest/v1/{table}"

def new_uuid() -> str:
    return str(uuid.uuid4())

def upsert_one(table: str, row: Dict[str, Any], conflict_cols: str) -> Dict[str, Any]:
    """
    Upsert a single row via PostgREST.
    conflict_cols: comma-separated unique constraint columns, e.g. "shop_domain"
    """
    url = _rest_url(table)
    h = _headers()
    h["Prefer"] = "resolution=merge-duplicates,return=representation"
    params = {"on_conflict": conflict_cols}

    r = requests.post(url, headers=h, params=params, json=[row], timeout=30)
    if r.status_code not in (200, 201):
        raise SupabaseAdminError(f"Supabase upsert failed ({table}): {r.status_code} {r.text}")

    data = r.json()
    if not data:
        return row
    return data[0]

def select_one(table: str, filters: Dict[str, str], columns: str = "*") -> Optional[Dict[str, Any]]:
    url = _rest_url(table)
    h = _headers()
    params = {"select": columns}
    for k, v in filters.items():
        params[k] = f"eq.{v}"

    r = requests.get(url, headers=h, params=params, timeout=30)
    if r.status_code != 200:
        raise SupabaseAdminError(f"Supabase select failed ({table}): {r.status_code} {r.text}")
    data = r.json()
    if not data:
        return None
    return data[0]

def update_where(table: str, filters: Dict[str, str], patch: Dict[str, Any]) -> int:
    url = _rest_url(table)
    h = _headers()
    h["Prefer"] = "return=minimal"
    params = {}
    for k, v in filters.items():
        params[k] = f"eq.{v}"

    r = requests.patch(url, headers=h, params=params, json=patch, timeout=30)
    if r.status_code not in (200, 204):
        raise SupabaseAdminError(f"Supabase update failed ({table}): {r.status_code} {r.text}")
    return 1
