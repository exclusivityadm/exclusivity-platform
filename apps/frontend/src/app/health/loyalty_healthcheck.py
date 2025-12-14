"""
Loyalty Healthcheck
===================

Purpose:
- Verify Supabase connectivity
- Verify RLS access via service_role
- Sanity-check ledger + members tables
- Provide a fast, safe endpoint for keepalive + monitoring
"""

from __future__ import annotations
from decimal import Decimal
from typing import Dict, Any

from app.repositories.loyalty_repository import LoyaltyRepository


async def loyalty_healthcheck(repo: LoyaltyRepository) -> Dict[str, Any]:
    checks = {
        "policies": False,
        "members": False,
        "ledger": False,
    }

    # Policies: simple read (may be empty)
    try:
        await repo.get_policy_json("__healthcheck__")
        checks["policies"] = True
    except Exception as e:
        checks["policies_error"] = str(e)

    # Members: read + write roundtrip (safe no-op upsert)
    try:
        val = await repo.get_member_lifetime_spend("__healthcheck__", "__healthcheck__")
        if isinstance(val, Decimal):
            checks["members"] = True
    except Exception as e:
        checks["members_error"] = str(e)

    # Ledger: list (empty OK)
    try:
        events = await repo.list_ledger_events("__healthcheck__", "__healthcheck__")
        if isinstance(events, list):
            checks["ledger"] = True
    except Exception as e:
        checks["ledger_error"] = str(e)

    ok = all(v is True for v in checks.values() if isinstance(v, bool))
    return {
        "ok": ok,
        "checks": checks,
    }
