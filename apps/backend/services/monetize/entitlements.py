from __future__ import annotations

from typing import Dict, Any
from apps.backend.db import get_supabase


def get_plan_for_merchant(merchant_id: str) -> str:
    """
    Source of truth:
    - If monetize module is already assigning plans, this reads it.
    - Otherwise defaults to 'preview'.
    """
    sb = get_supabase()
    if not sb:
        return "preview"

    # If you already have a monetize table, keep it.
    # If not, this safely defaults.
    try:
        r = sb.table("merchant_plans").select("plan").eq("merchant_id", merchant_id).limit(1).execute()
        if r.data and (r.data[0] or {}).get("plan"):
            return str(r.data[0]["plan"])
    except Exception:
        return "preview"

    return "preview"


def can_execute_actions(plan: str) -> bool:
    """
    Preview = suggest only.
    Paid tiers = execute.
    """
    return plan.lower().strip() not in ["preview", "free"]
