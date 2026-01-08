# apps/backend/services/action_router.py
# =====================================================
# AI Action Router — FINAL (Drop F)
# =====================================================

from typing import Dict, Any
from apps.backend.services.action_ledger import record_action
from apps.backend.services.kill_switch import execution_allowed
from apps.backend.services.replay_guard import action_fingerprint, is_replay
from apps.backend.services.rate_guard import allow_action

def preview_action(action: Dict[str, Any]) -> Dict[str, Any]:
    record_action({
        "merchant_id": action.get("merchant_id"),
        "mode": "preview",
        "action_type": action.get("type"),
        "payload": action,
        "allowed": True,
        "executed": False,
    })

    return {
        "ok": True,
        "mode": "preview",
        "message": "Preview only. No execution performed.",
        "action": action,
    }

def execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    merchant_id = action.get("merchant_id")

    if not execution_allowed(merchant_id):
        record_action({
            "merchant_id": merchant_id,
            "mode": "execute",
            "action_type": action.get("type"),
            "payload": action,
            "allowed": False,
            "executed": False,
        })
        return {"ok": False, "message": "Execution disabled"}

    if not allow_action(merchant_id):
        return {"ok": False, "message": "Rate limit exceeded"}

    fp = action_fingerprint(action)
    if is_replay(fp):
        return {"ok": False, "message": "Replay blocked"}

    record_action({
        "merchant_id": merchant_id,
        "mode": "execute",
        "action_type": action.get("type"),
        "payload": action,
        "allowed": True,
        "executed": True,
    })

    return {
        "ok": True,
        "mode": "execute",
        "message": "Action executed",
        "action": action,
    }
