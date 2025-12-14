from __future__ import annotations
from typing import Dict, Any
from decimal import Decimal

from apps.backend.repositories.loyalty_repository import LoyaltyRepository


async def loyalty_healthcheck(repo: LoyaltyRepository) -> Dict[str, Any]:
    checks = {"policies": False, "members": False, "ledger": False}

    try:
        await repo.get_policy_json("__health__")
        checks["policies"] = True
    except Exception as e:
        checks["policies_error"] = str(e)

    try:
        val = await repo.get_member_lifetime_spend("__health__", "__health__")
        if isinstance(val, Decimal):
            checks["members"] = True
    except Exception as e:
        checks["members_error"] = str(e)

    try:
        events = await repo.list_ledger_events("__health__", "__health__")
        if isinstance(events, list):
            checks["ledger"] = True
    except Exception as e:
        checks["ledger_error"] = str(e)

    return {"ok": all(checks.values()), "checks": checks}
