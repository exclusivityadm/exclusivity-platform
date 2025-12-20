from __future__ import annotations

from typing import Dict, Any


def preview_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns what would happen, but does not execute anything.
    """
    return {
        "ok": True,
        "mode": "preview",
        "action": action,
        "message": "Preview tier: I can propose actions, but I won’t execute changes until you upgrade.",
    }


def execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute actions (paid tiers).
    For now we keep this conservative: execution = enqueue tasks / set internal flags,
    not directly pushing price updates unless explicitly built later.
    """
    action_type = (action or {}).get("type") or ""

    # Future: route to real executors
    if action_type == "pricing.apply_default_buffer":
        return {
            "ok": True,
            "mode": "execute",
            "action": action,
            "message": "Pricing buffer has been approved in Exclusivity. Next step is applying it to Shopify prices (requires explicit confirmation and scopes).",
        }

    return {"ok": False, "mode": "execute", "action": action, "message": f"Unknown action type: {action_type}"}
