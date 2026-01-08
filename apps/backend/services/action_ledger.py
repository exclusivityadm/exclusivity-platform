# apps/backend/services/action_ledger.py
# =====================================================
# Canonical Action Ledger — Drop F
# Every AI action (preview OR execute) is recorded
# =====================================================

from __future__ import annotations
import time
from typing import Dict, Any
import requests
import os
import json

def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def _sb_headers() -> Dict[str, str]:
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

def _sb_url(path: str) -> str:
    return _env("SUPABASE_URL").rstrip("/") + path

def record_action(event: Dict[str, Any]) -> None:
    """
    event must include:
      - merchant_id
      - mode: preview | execute
      - action_type
      - payload
      - allowed (bool)
    """
    row = {
        "merchant_id": event["merchant_id"],
        "mode": event["mode"],
        "action_type": event.get("action_type", "unknown"),
        "payload": event.get("payload", {}),
        "allowed": bool(event.get("allowed")),
        "executed": bool(event.get("executed", False)),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    r = requests.post(
        _sb_url("/rest/v1/action_ledger"),
        headers=_sb_headers(),
        data=json.dumps(row),
        timeout=15,
    )

    if r.status_code >= 400:
        raise RuntimeError(f"Action ledger write failed: {r.text}")
