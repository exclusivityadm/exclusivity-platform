# apps/backend/services/action_ledger.py
import time, json
from typing import Dict, Any
from apps.backend.services.supabase_admin import insert_row

def record_action(
    merchant_id: str,
    mode: str,
    action: Dict[str, Any],
    plan: str,
    executed: bool,
    result: Dict[str, Any],
):
    row = {
        "merchant_id": merchant_id,
        "mode": mode,               # preview | execute
        "plan": plan,
        "executed": executed,
        "action": action,
        "result": result,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    insert_row("action_ledger", row)
