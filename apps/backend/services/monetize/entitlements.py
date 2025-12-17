from typing import Any, Dict
from apps.backend.services.monetize.repository import (
    get_active_plan_key_for_merchant,
    get_plan,
    get_entitlements,
)

def resolve_merchant_entitlements(merchant_id: str) -> Dict[str, Any]:
    plan_key = get_active_plan_key_for_merchant(merchant_id)
    plan = get_plan(plan_key)
    ent = get_entitlements(plan_key)

    return {
        "merchant_id": merchant_id,
        "plan": plan,
        "entitlements": ent,
    }

def has_entitlement(merchant_id: str, entitlement_key: str, default: bool = True) -> bool:
    """
    Graceful gating:
    - If entitlement not defined, returns default (fails open by default).
    - If defined, respects enabled flag.
    """
    data = resolve_merchant_entitlements(merchant_id)
    ent = data.get("entitlements") or {}
    if entitlement_key not in ent:
        return bool(default)
    return bool(ent[entitlement_key].get("enabled", default))
