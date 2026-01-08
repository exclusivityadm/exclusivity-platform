# apps/backend/services/action_router.py
# =====================================================
# AI Action Router — Canonical Dispatcher (FINAL)
# =====================================================

from typing import Dict, Any

from apps.backend.services.action_ledger import write_action_ledger
from apps.backend.services.monetize.entitlements import (
    get_plan_for_merchant,
    can_execute_actions,
)

# -----------------------------------------------------
# Preview (advisory only)
# -----------------------------------------------------

def preview_action(
    action: Dict[str, Any],
    *,
    merchant_id: str,
    persona: str,
) -> Dict[str, Any]:
    write_action_ledger(
        merchant_id=merchant_id,
        mode="preview",
        plan="preview",
        allowed=True,
        action=action,
        persona=persona,
        result={"preview": True},
    )

    return {
        "ok": True,
        "mode": "preview",
        "action": action,
        "message": "Preview only. No execution performed.",
    }


# -----------------------------------------------------
# Execute (tier-gated)
# -----------------------------------------------------

def execute_action(
    action: Dict[str, Any],
    *,
    merchant_id: str,
    persona: str,
) -> Dict[str, Any]:
    plan = get_plan_for_merchant(merchant_id)

    if not can_execute_actions(plan):
        write_action_ledger(
            merchant_id=merchant_id,
            mode="execute",
            plan=plan,
            allowed=False,
            action=action,
            persona=persona,
            reason="plan_not_entitled",
        )
        return {
            "ok": False,
            "status_code": 403,
            "plan": plan,
            "message": "Plan not entitled to execute actions.",
        }

    action_type = (action.get("type") or "").lower()

    if action_type == "award_loyalty":
        from apps.backend.services.execution.loyalty import execute_award_loyalty
        result = execute_award_loyalty(merchant_id, action)

    elif action_type == "shopify_tag":
        from apps.backend.services.execution.shopify import execute_shopify_tag
        result = execute_shopify_tag(merchant_id, action)

    else:
        write_action_ledger(
            merchant_id=merchant_id,
            mode="execute",
            plan=plan,
            allowed=False,
            action=action,
            persona=persona,
            reason="unknown_action_type",
        )
        return {
            "ok": False,
            "message": f"Unknown action type: {action_type}",
        }

    write_action_ledger(
        merchant_id=merchant_id,
        mode="execute",
        plan=plan,
        allowed=True,
        action=action,
        persona=persona,
        result=result,
    )

    return {
        "ok": True,
        "mode": "execute",
        "action": action,
        "result": result,
    }
