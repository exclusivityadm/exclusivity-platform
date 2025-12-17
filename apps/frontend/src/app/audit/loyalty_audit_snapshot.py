"""
Loyalty Audit Snapshot
======================

Purpose:
- Produce deterministic daily snapshots
- Useful for audits, reconciliation, and AI explanations
- No writes by default (caller decides persistence)
"""

from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any

from app.services.loyalty.loyalty_service import LoyaltyService


async def generate_loyalty_snapshot(
    *,
    svc: LoyaltyService,
    merchant_id: str,
) -> Dict[str, Any]:
    """
    Snapshot summary for a merchant.
    """
    now = datetime.now(timezone.utc)

    # NOTE: Repository can add aggregate helpers later.
    # For now this is a structural placeholder that
    # establishes the snapshot contract.
    policy = await svc.get_policy(merchant_id)

    snapshot = {
        "merchant_id": merchant_id,
        "policy_version": policy.version,
        "generated_at": now.isoformat(),
        "notes": "Daily loyalty snapshot (structure stable, aggregates pluggable).",
    }

    return snapshot
