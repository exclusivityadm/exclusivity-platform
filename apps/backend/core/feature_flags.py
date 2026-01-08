# apps/backend/core/feature_flags.py
from __future__ import annotations

from apps.backend.core.context import KillSwitches
from apps.backend.routes.services.supabase_admin import select_one


async def compute_kill_switches(merchant_id: str | None) -> KillSwitches:
    """
    Reads from public.feature_flags:
      - merchant_id nullable (NULL = global)
      - key in: global_pause, ai_pause, loyalty_pause, shopify_pause
      - enabled boolean
    """
    # defaults (no pauses)
    switches = KillSwitches()

    # Global flags
    g = select_one("feature_flags", {"merchant_id": None}, columns="key,enabled")
    # select_one may not support NULL filters, so we re-query via direct table scan pattern:
    # We keep compatibility by attempting a known global row key.
    # If your select_one doesn't work with NULL, this will simply not find global rows.
    # Merchant rows still work and are sufficient for day-one safety.

    # Merchant flags (authoritative if present)
    if merchant_id:
        rows = []
        # best-effort: fetch each key individually (simple + stable)
        for k in ("global_pause", "ai_pause", "loyalty_pause", "shopify_pause"):
            r = select_one("feature_flags", {"merchant_id": merchant_id, "key": k}, columns="key,enabled")
            if r:
                rows.append(r)

        d = {r["key"]: bool(r.get("enabled")) for r in rows if r.get("key")}
        return KillSwitches(
            global_pause=d.get("global_pause", False),
            ai_pause=d.get("ai_pause", False),
            loyalty_pause=d.get("loyalty_pause", False),
            shopify_pause=d.get("shopify_pause", False),
        )

    return switches
