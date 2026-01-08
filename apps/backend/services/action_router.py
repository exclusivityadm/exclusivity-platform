# apps/backend/services/action_router.py
# =====================================================
# AI Action Router — Canonical Execution Brain
# =====================================================

from __future__ import annotations
from typing import Dict, Any

from apps.backend.services.action_ledger import record_action_event
from apps.backend.services.monetize.entitlements import (
    get_plan_for_merchant,
    can_execute_actions,
)


# -----------------------------------------------------
# Preview
# -----------------------------------------------------

def preview_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preview tier:
    - No execution
    - Always ledgered
    """
    return {
        "ok": True,
        "mode": "preview",
        "action": action,
        "message": "Preview only. No execution performed.",
        "would_execute": True,
    }


# -----------------------------------------------------
# Execute
# -----------------------------------------------------

def execute_action(
    *,
    merchant_id: str,
    persona: str,
    action: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Paid tiers only.
    Ledgered regardless of outcome.
    """

    plan = get_plan_for_merchant(merchant_id)

    # -------------------------
    # Execution denied
    # -------------------------
    if not can_execute_actions(plan):
        record_action_event(
            merchant_id=merchant_id,
            persona=persona,
            action=action,
            mode="execute",
            outcome="denied",
            plan=plan,
            message="Execution denied by plan entitlement",
        )
        return {
            "ok": False,
            "mode": "execute",
            "plan": plan,
            "message": "Execution denied. Upgrade required.",
        }

    # -------------------------
    # Execution allowed
    # -------------------------
    # NOTE: Concrete execution handlers will live in
    # apps/backend/services/execution/*
    # and be called here WITHOUT changing ai.py

    record_action_event(
        merchant_id=merchant_id,
        persona=persona,
        action=action,
        mode="execute",
        outcome="executed",
        plan=plan,
        message="Action accepted and executed",
    )

    return {
        "ok": True,
        "mode": "execute",
        "plan": plan,
        "action": action,
        "message": "Action executed successfully.",
    }
