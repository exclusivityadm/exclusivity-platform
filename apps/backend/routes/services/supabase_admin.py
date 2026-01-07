# apps/backend/routes/services/supabase_admin.py
# =====================================================
# Supabase Admin Helpers (Service Role, Server-Side ONLY)
#
# Provides canonical helpers used by backend routes:
#   - select_one(table, match, columns="*")
#   - insert_one(table, row, columns="*")
#   - update_one(table, match, values, columns="*")
#
# Uses Supabase PostgREST:
#   {SUPABASE_URL}/rest/v1/<table>
#
# Required env:
#   SUPABASE_URL
#   SUPABASE_SERVICE_ROLE_KEY
#
# Notes:
# - This bypasses RLS because it uses the service role key.
# - Never call these from the frontend.
# =====================================================

from __future__ import annotations

import os
import json
import requests
from typing import Any, Dict, Optional


class SupabaseAdminError(Exception):
    pass


def _env(name: str) -> str:
    v = (os.getenv(name) or "").strip()
    if not v:
        raise SupabaseAdminError(f"Missing environment variable: {name}")
    return v


def _base_url() -> str:
    url = _env("SUPABASE_URL").rstrip("/")
    return url


def _headers() -> Dict[str, str]:
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _table_url(table: str) -> str:
    t = (table or "").strip()
    if not t:
        raise SupabaseAdminError("Missing table name")
    return f"{_base_url()}/rest/v1/{t}"


def _apply_filters(params: Dict[str, str], match: Dict[str, Any]) -> Dict[str, str]:
    """
    Converts match dict into PostgREST filters.
    Example:
      match={"merchant_id":"uuid"} -> params["merchant_id"] = "eq.uuid"
    """
    if not match:
        return params
    for k, v in match.items():
        if v is None:
            continue
        params[str(k)] = f"eq.{v}"
    return params


def _handle(resp: requests.Response, context: str) -> Any:
    """
    Raise SupabaseAdminError with useful context if non-2xx.
    """
    if 200 <= resp.status_code < 300:
        if resp.text.strip() == "":
            return None
        try:
            return resp.json()
        except Exception:
            return resp.text

    body = resp.text
    # Try to parse JSON error shape
    try:
        body_json = resp.json()
        body = json.dumps(body_json, ensure_ascii=False)
    except Exception:
        pass

    raise SupabaseAdminError(
        f"{context} failed: status={resp.status_code} body={body}"
    )


# =====================================================
# READ
# =====================================================

def select_one(table: str, match: Dict[str, Any], columns: str = "*") -> Optional[Dict[str, Any]]:
    """
    Select a single row by match dict. Returns dict or None.
    """
    url = _table_url(table)
    params: Dict[str, str] = {"select": columns, "limit": "1"}
    params = _apply_filters(params, match)

    resp = requests.get(url, headers=_headers(), params=params, timeout=30)
    data = _handle(resp, f"select_one({table})")

    # PostgREST returns a list of rows
    if isinstance(data, list) and len(data) > 0:
        row = data[0]
        return row if isinstance(row, dict) else None
    return None


# =====================================================
# WRITE
# =====================================================

def insert_one(table: str, row: Dict[str, Any], columns: str = "*") -> Optional[Dict[str, Any]]:
    """
    Insert a single row.
    Returns inserted row (representation) when possible, else None.
    """
    if not isinstance(row, dict) or not row:
        raise SupabaseAdminError("insert_one requires a non-empty dict row")

    url = _table_url(table)
    headers = _headers()
    # Ask PostgREST to return the inserted row
    headers["Prefer"] = "return=representation"

    params: Dict[str, str] = {"select": columns} if columns else {}
    resp = requests.post(url, headers=headers, params=params, data=json.dumps(row), timeout=30)
    data = _handle(resp, f"insert_one({table})")

    # Usually returns a list with one row
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        return data[0]
    # Some configurations return dict directly
    if isinstance(data, dict):
        return data
    return None


def update_one(table: str, match: Dict[str, Any], values: Dict[str, Any], columns: str = "*") -> Optional[Dict[str, Any]]:
    """
    Update rows matching `match` with `values`.
    Returns the first updated row (representation) when possible, else None.
    """
    if not match or not isinstance(match, dict):
        raise SupabaseAdminError("update_one requires a non-empty match dict")
    if not isinstance(values, dict) or not values:
        raise SupabaseAdminError("update_one requires a non-empty values dict")

    url = _table_url(table)
    headers = _headers()
    headers["Prefer"] = "return=representation"

    params: Dict[str, str] = {"select": columns} if columns else {}
    params = _apply_filters(params, match)

    resp = requests.patch(url, headers=headers, params=params, data=json.dumps(values), timeout=30)
    data = _handle(resp, f"update_one({table})")

    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict):
        return data
    return None
