from __future__ import annotations

from typing import Any, Dict, Optional

from apps.backend.routes.services.supabase_admin import select_one, insert_one

# Canonical policy:
# - preview plan: AI can only PREVIEW (advise)
# - paid plans: AI can EXECUTE
PAID_PLANS = {"paid_tier_1", "paid_tier_2", "enterprise"}

def get_merchant_plan(merchant_id: str) -> str:
    sub = select_one("merchant_subscription", {"merchant_id": merchant_id})
    if not sub:
        return "preview"
    return str(sub.get("plan") or "preview")

def can_execute(merchant_id: str) -> bool:
    return get_merchant_plan(merchant_id) in PAID_PLANS

def log_action_request(
    *,
    merchant_id: str,
    mode: str,
    action_type: str,
    source: str,
    source_ref: Optional[str],
    request_payload: Dict[str, Any],
    status: str,
    decision: Optional[str],
    result: Dict[str, Any],
) -> Dict[str, Any]:
    row = {
        "merchant_id": merchant_id,
        "mode": mode,
        "action_type": action_type,
        "source": source,
        "source_ref": source_ref,
        "request": request_payload or {},
        "status": status,
        "decision": decision,
        "result": result or {},
    }
    # Idempotency enforced by DB unique index; duplicates are ok to treat as safe.
    return insert_one("ai_action_requests", row)

def enforce_execution_policy(merchant_id: str) -> Dict[str, Any]:
    plan = get_merchant_plan(merchant_id)
    if plan == "preview":
        return {
            "allowed": False,
            "plan": plan,
            "reason": "preview_tier_advise_only",
        }
    if plan in PAID_PLANS:
        return {"allowed": True, "plan": plan}
    return {"allowed": False, "plan": plan, "reason": "plan_not_allowed"}
