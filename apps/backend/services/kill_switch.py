# apps/backend/services/kill_switch.py
# =====================================================
# Execution Kill Switch — Drop F
# =====================================================

import os
from typing import Optional
import requests

def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def _sb_headers():
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

def _sb_url(path: str) -> str:
    return _env("SUPABASE_URL").rstrip("/") + path

def execution_allowed(merchant_id: str) -> bool:
    # Global kill switch
    if os.getenv("EXECUTION_KILL_SWITCH", "").lower() == "true":
        return False

    # Per-merchant kill switch
    r = requests.get(
        _sb_url(f"/rest/v1/merchant_flags?merchant_id=eq.{merchant_id}&select=execution_disabled"),
        headers=_sb_headers(),
        timeout=10,
    )

    if r.status_code >= 400:
        return False

    rows = r.json()
    if rows and rows[0].get("execution_disabled") is True:
        return False

    return True
