# apps/backend/services/action_ledger.py
# =====================================================
# Action Ledger — Canonical, Immutable, Day-One
#
# Records ALL AI actions:
# - previews
# - denied executions
# - successful executions
#
# Append-only. No updates. No deletes.
# =====================================================

from __future__ import annotations
from typing import Dict, Any
import time
import uuid
import os
import json
import requests


# -----------------------------------------------------
# Supabase (service role only)
# -----------------------------------------------------

def _env(name: str) -> str:
    v = (os.getenv(name) or "").strip()
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


def _sb_headers() -> Dict[str, str]:
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _sb_url(path: str) -> str:
    return _env("SUPABASE_URL").rstrip("/") + path


def _sb_insert(table: str, row: Dict[str, Any]) -> None:
    h = _sb_headers()
    h["Prefer"] = "return=minimal"
    r = requests.post(
        _sb_url(f"/rest/v1/{table}"),
        headers=h,
        data=json.dumps(row),
        timeout=30,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Action ledger insert failed: {r.text}")


# -----------------------------------------------------
# Public API
# -----------------------------------------------------

def record_action_event(
    *,
    merchant_id: str,
    persona: str,
    action: Dict[str, Any],
    mode: str,              # preview | execute
    outcome: str,           # allowed | denied | executed | failed
    plan: str,
    message: str,
) -> Dict[str, Any]:
    """
    Canonical action ledger writer.
    ALWAYS called exactly once per AI action decision.
    """

    event_id = str(uuid.uuid4())
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    row = {
        "event_id": event_id,
        "merchant_id": merchant_id,
        "persona": persona,
        "action_type": action.get("type"),
        "action_payload": action,
        "mode": mode,
        "outcome": outcome,
        "plan": plan,
        "message": message,
        "created_at": now_iso,
    }

    _sb_insert("action_ledger", row)

    return {
        "ok": True,
        "event_id": event_id,
        "mode": mode,
        "outcome": outcome,
    }
