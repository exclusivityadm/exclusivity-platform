# apps/backend/services/action_ledger.py
# =====================================================
# Action Ledger (Canonical)
#
# RULES (LOCKED):
# - Ledger ALL actions:
#     • preview
#     • execute
#     • denied / blocked
# - Service-role only writes
# - Best-effort: never break execution flow
# =====================================================

from __future__ import annotations

import os
import json
import time
from typing import Any, Dict, Optional

import requests


# -----------------------------------------------------
# Env helpers
# -----------------------------------------------------

def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()

def _must_env(name: str) -> str:
    v = _env(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


# -----------------------------------------------------
# Supabase (service role)
# -----------------------------------------------------

def _sb_headers() -> Dict[str, str]:
    key = _must_env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _sb_url(path: str) -> str:
    return _must_env("SUPABASE_URL").rstrip("/") + path


# -----------------------------------------------------
# Public API
# -----------------------------------------------------

def write_action_ledger(
    *,
    merchant_id: str,
    mode: str,                 # "preview" | "execute"
    plan: str,
    allowed: bool,
    action: Dict[str, Any],
    persona: Optional[str] = None,
    request_id: Optional[str] = None,
    reason: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Best-effort ledger write.
    This MUST NEVER throw upstream.
    """
    try:
        row = {
            "merchant_id": merchant_id,
            "mode": mode,
            "plan": plan,
            "allowed": bool(allowed),
            "persona": persona,
            "request_id": request_id,
            "reason": reason,
            "action": action,
            "result": result,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        headers = _sb_headers()
        headers["Prefer"] = "return=minimal"

        r = requests.post(
            _sb_url("/rest/v1/action_ledger"),
            headers=headers,
            data=json.dumps(row),
            timeout=30,
        )

        # Ignore duplicates / conflicts silently
        if r.status_code >= 400:
            txt = (r.text or "").lower()
            if "duplicate" in txt or "unique" in txt:
                return
            return

    except Exception:
        # Ledger failures must NEVER block execution
        return
