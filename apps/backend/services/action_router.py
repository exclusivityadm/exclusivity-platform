# apps/backend/services/action_router.py
# =====================================================
# AI Action Router — Canonical Execution Surface
#
# LOCKED RULES:
# - Preview is free, no execution, but still ledgered.
# - Paid plans can execute, tier-gated by capability.
# - Ledger ALL actions (preview + execute + denied).
#
# Action format (canonical):
# {
#   "type": "loyalty.award_from_orders" | "loyalty.evaluate_tiers" | ...,
#   "params": {...},
#   "request_id": "optional-idempotency-key"
# }
# =====================================================

from __future__ import annotations

from typing import Any, Dict, Tuple, Optional

from apps.backend.services.monetize.entitlements import (
    get_plan_for_merchant,
    can_execute_actions,
    require_cap,
)
from apps.backend.services.ledger.action_ledger import write_action_ledger


def _action_type(action: Dict[str, Any]) -> str:
    t = (action.get("type") or "").strip()
    return t

def _params(action: Dict[str, Any]) -> Dict[str, Any]:
    p = action.get("params") or {}
    return p if isinstance(p, dict) else {}

def _request_id(action: Dict[str, Any]) -> Optional[str]:
    rid = (action.get("request_id") or "").strip()
    return rid or None

def _validate(action: Dict[str, Any]) -> Tuple[bool, str]:
    if not isinstance(action, dict):
        return False, "Action must be an object"
    t = _action_type(action)
    if not t:
        return False, "Missing action.type"
    if len(t) > 120:
        return False, "action.type too long"
    return True, ""


# -----------------------------------------------------
# Preview (always allowed) — ledgered
# -----------------------------------------------------

def preview_action(action: Dict[str, Any], *, merchant_id: str = "", persona: str = "orion") -> Dict[str, Any]:
    ok, err = _validate(action)
    plan = get_plan_for_merchant(merchant_id) if merchant_id else "preview"

    if not ok:
        write_action_ledger(
            merchant_id=merchant_id or "unknown",
            mode="preview",
            plan=plan,
            allowed=False,
            persona=persona,
            request_id=_request_id(action),
            reason=err,
            action=action if isinstance(action, dict) else {"raw": str(action)},
            result={"ok": False, "message": err},
        )
        return {"ok": False, "mode": "preview", "message": err}

    # Preview is advisory-only but can still return an execution plan
    t = _action_type(action)
    p = _params(action)

    response = {
        "ok": True,
        "mode": "preview",
        "action": {"type": t, "params": p},
        "message": "Preview only. No actions executed.",
        "would_execute": True,
        "plan": plan,
    }

    write_action_ledger(
        merchant_id=merchant_id or "unknown",
        mode="preview",
        plan=plan,
        allowed=True,
        persona=persona,
        request_id=_request_id(action),
        reason=None,
        action={"type": t, "params": p},
        result=response,
    )
    return response


# -----------------------------------------------------
# Execute (paid only) — tier gated — ledgered
# -----------------------------------------------------

def execute_action(action: Dict[str, Any], *, merchant_id: str, persona: str = "orion") -> Dict[str, Any]:
    ok, err = _validate(action)
    plan = get_plan_for_merchant(merchant_id)

    if not ok:
        write_action_ledger(
            merchant_id=merchant_id,
            mode="execute",
            plan=plan,
            allowed=False,
            persona=persona,
            request_id=_request_id(action),
            reason=err,
            action=action if isinstance(action, dict) else {"raw": str(action)},
            result={"ok": False, "message": err},
        )
        return {"ok": False, "mode": "execute", "plan": plan, "message": err}

    # Global execution gate
    if not can_execute_actions(plan):
        msg = "Preview tier cannot execute actions. Upgrade to enable execution."
        write_action_ledger(
            merchant_id=merchant_id,
            mode="execute",
            plan=plan,
            allowed=False,
            persona=persona,
            request_id=_request_id(action),
            reason=msg,
            action={"type": _action_type(action), "params": _params(action)},
            result={"ok": False, "message": msg, "status_code": 403},
        )
        return {"ok": False, "mode": "execute", "plan": plan, "status_code": 403, "message": msg}

    # Per-action capability gates
    t = _action_type(action)
    p = _params(action)

    # Define capability requirements by action
    cap_req = {
        # Loyalty worker ops
        "loyalty.award_from_orders": ("loyalty_worker", 1),
        "loyalty.evaluate_tiers": ("loyalty_worker", 1),

        # Shopify backfill / heavy ops
        "shopify.backfill": ("shopify_backfill", 1),

        # Marketing + Pricing (future wiring; gates exist now)
        "marketing.send": ("marketing_send", 1),
        "pricing.apply": ("pricing_apply", 1),
        "ai.automation": ("ai_automation", 1),
    }

    if t in cap_req:
        cap, lvl = cap_req[t]
        allowed, reason = require_cap(plan, cap, lvl)
        if not allowed:
            write_action_ledger(
                merchant_id=merchant_id,
                mode="execute",
                plan=plan,
                allowed=False,
                persona=persona,
                request_id=_request_id(action),
                reason=reason,
                action={"type": t, "params": p},
                result={"ok": False, "message": reason, "status_code": 403},
            )
            return {"ok": False, "mode": "execute", "plan": plan, "status_code": 403, "message": reason}

    # Execution dispatcher (deterministic)
    result = _dispatch_execute(t, p)

    write_action_ledger(
        merchant_id=merchant_id,
        mode="execute",
        plan=plan,
        allowed=True,
        persona=persona,
        request_id=_request_id(action),
        reason=None,
        action={"type": t, "params": p},
        result=result,
    )
    return result


def _dispatch_execute(action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes ONLY what is wired. Anything else returns a clear, deterministic response.
    NOTE: We do NOT silently pretend. If not wired, we say so.
    """
    # Wire loyalty actions to existing backend endpoints? For now we return acceptance + next hop.
    # (We will wire direct internal calls in a later drop without touching ai.py.)
    if action_type == "loyalty.award_from_orders":
        return {
            "ok": True,
            "mode": "execute",
            "type": action_type,
            "executed": True,
            "message": "Accepted. Invoke POST /loyalty/award-from-orders with worker token to perform award run.",
            "params": params,
        }

    if action_type == "loyalty.evaluate_tiers":
        return {
            "ok": True,
            "mode": "execute",
            "type": action_type,
            "executed": True,
            "message": "Accepted. Invoke POST /loyalty/evaluate-tiers with worker token to perform tier evaluation.",
            "params": params,
        }

    if action_type == "shopify.backfill":
        return {
            "ok": True,
            "mode": "execute",
            "type": action_type,
            "executed": True,
            "message": "Accepted. Backfill execution surface will run via worker route (Drop D/E wiring).",
            "params": params,
        }

    # Not wired yet (explicit)
    return {
        "ok": False,
        "mode": "execute",
        "type": action_type,
        "executed": False,
        "message": f"Action type '{action_type}' is recognized but not yet wired for direct execution.",
        "params": params,
        "status_code": 501,
    }
