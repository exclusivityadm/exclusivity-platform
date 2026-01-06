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
        raise SupabaseAdminError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _rest_url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"

def new_uuid() -> str:
    return str(uuid.uuid4())

def rpc(function_name: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
    r = requests.post(url, headers=_headers(), json=payload, timeout=30)
    if r.status_code != 200:
        raise SupabaseAdminError(f"RPC {function_name} failed: {r.status_code} {r.text}")
    return r.json()

def insert_one(table: str, row: Dict[str, Any]) -> Dict[str, Any]:
    h = _headers()
    h["Prefer"] = "return=representation"
    r = requests.post(_rest_url(table), headers=h, json=[row], timeout=30)
    if r.status_code not in (200, 201):
        raise SupabaseAdminError(f"Insert failed ({table}): {r.status_code} {r.text}")
    data = r.json()
    return data[0] if data else row

def upsert_one(table: str, row: Dict[str, Any], conflict_cols: str) -> Dict[str, Any]:
    h = _headers()
    h["Prefer"] = "resolution=merge-duplicates,return=representation"
    r = requests.post(
        _rest_url(table),
        headers=h,
        params={"on_conflict": conflict_cols},
        json=[row],
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise SupabaseAdminError(f"Upsert failed ({table}): {r.status_code} {r.text}")
    data = r.json()
    return data[0] if data else row

def select_one(table: str, filters: Dict[str, str], columns: str = "*") -> Optional[Dict[str, Any]]:
    params = {"select": columns}
    for k, v in filters.items():
        params[k] = f"eq.{v}"
    r = requests.get(_rest_url(table), headers=_headers(), params=params, timeout=30)
    if r.status_code != 200:
        raise SupabaseAdminError(f"Select failed ({table}): {r.status_code} {r.text}")
    data = r.json()
    return data[0] if data else None

def update_where(table: str, filters: Dict[str, str], patch: Dict[str, Any]) -> None:
    params = {k: f"eq.{v}" for k, v in filters.items()}
    h = _headers()
    h["Prefer"] = "return=minimal"
    r = requests.patch(_rest_url(table), headers=h, params=params, json=patch, timeout=30)
    if r.status_code not in (200, 204):
        raise SupabaseAdminError(f"Update failed ({table}): {r.status_code} {r.text}")
