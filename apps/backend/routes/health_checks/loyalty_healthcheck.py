from __future__ import annotations

from typing import Dict, Any

from ..repositories.loyalty_repository import create_supabase_client_from_env


async def loyalty_healthcheck() -> Dict[str, Any]:
    """
    Lightweight health check for loyalty subsystem.
    Verifies:
    - Supabase connectivity
    - Required tables are accessible
    """

    sb = create_supabase_client_from_env()

    checks = {}

    try:
        sb.table("loyalty_policies").select("id").limit(1).execute()
        checks["loyalty_policies"] = True
    except Exception:
        checks["loyalty_policies"] = False

    try:
        sb.table("loyalty_members").select("id").limit(1).execute()
        checks["loyalty_members"] = True
    except Exception:
        checks["loyalty_members"] = False

    try:
        sb.table("loyalty_ledger").select("id").limit(1).execute()
        checks["loyalty_ledger"] = True
    except Exception:
        checks["loyalty_ledger"] = False

    ok = all(checks.values())

    return {
        "ok": ok,
        "checks": checks,
    }
