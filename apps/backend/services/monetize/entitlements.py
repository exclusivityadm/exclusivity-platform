# apps/backend/services/monetize/entitlements.py
# =====================================================
# Monetize — Entitlements (Canonical)
# =====================================================

from typing import Literal
from apps.backend.routes.services.supabase_admin import select_one

Plan = Literal["preview", "paid_tier_1", "paid_tier_2", "enterprise"]

PAID_PLANS = {"paid_tier_1", "paid_tier_2", "enterprise"}

def get_plan_for_merchant(merchant_id: str) -> Plan:
    """
    Returns merchant plan. Defaults to preview if not found.
    """
    sub = select_one("merchant_subscription", {"merchant_id": merchant_id})
    if not sub:
        return "preview"
    return str(sub.get("plan") or "preview")  # type: ignore

def can_execute_actions(plan: Plan) -> bool:
    """
    Preview = advise only
    Paid tiers = execution allowed
    """
    return plan in PAID_PLANS
