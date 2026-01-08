# apps/backend/services/monetize/entitlements.py

PLANS = {
    "preview": {
        "can_execute": False,
        "capabilities": [],
    },
    "starter": {
        "can_execute": True,
        "capabilities": ["loyalty"],
    },
    "growth": {
        "can_execute": True,
        "capabilities": ["loyalty", "pricing"],
    },
    "enterprise": {
        "can_execute": True,
        "capabilities": ["loyalty", "pricing", "marketing"],
    },
}

def get_plan_for_merchant(merchant_id: str) -> str:
    # canonical lookup (DB-backed later, deterministic now)
    return "preview"

def can_execute(plan: str, action_type: str) -> bool:
    p = PLANS.get(plan)
    return bool(p and p["can_execute"] and action_type in p["capabilities"])
