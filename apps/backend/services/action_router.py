# apps/backend/services/action_router.py
from typing import Dict, Any
from apps.backend.services.action_ledger import record_action
from apps.backend.services.execution.loyalty_executor import execute_loyalty
from apps.backend.services.execution.pricing_executor import execute_pricing
from apps.backend.services.execution.marketing_executor import execute_marketing

def preview_action(merchant_id: str, action: Dict[str, Any], plan: str):
    record_action(merchant_id, "preview", action, plan, False, {"preview": True})
    return {"ok": True, "preview": True, "action": action}

def execute_action(merchant_id: str, action: Dict[str, Any], plan: str):
    kind = action.get("type")

    if kind == "loyalty":
        result = execute_loyalty(merchant_id, action)
    elif kind == "pricing":
        result = execute_pricing(merchant_id, action)
    elif kind == "marketing":
        result = execute_marketing(merchant_id, action)
    else:
        result = {"ok": False, "error": "Unknown action type"}

    record_action(merchant_id, "execute", action, plan, True, result)
    return result
