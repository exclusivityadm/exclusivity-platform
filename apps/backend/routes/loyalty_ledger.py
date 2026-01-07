# apps/backend/routes/loyalty_ledger.py
# =====================================================
# Exclusivity Backend — Loyalty Ledger (Write-Only)
#
# Canonical append-only loyalty ledger.
#
# POST /loyalty/ledger/write
#
# Notes:
# - No tier logic
# - No notifications
# - No blockchain
# - Backend is source of truth
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
    insert_one,
)

router = APIRouter(tags=["loyalty"])


@router.post("/loyalty/ledger/write")
def write_loyalty_ledger(
    merchant_id: str,
    customer_id: str,
    event_type: str,
    delta: int,
    source: str = "system",
    preview: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Append a loyalty ledger entry.

    preview=true will calculate balance but not write.
    """

    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    if not customer_id:
        raise HTTPException(400, "Missing customer_id")

    if not event_type:
        raise HTTPException(400, "Missing event_type")

    if not isinstance(delta, int):
        raise HTTPException(400, "delta must be integer")

    metadata = metadata or {}

    try:
        # Fetch latest balance
        last = select_one(
            "loyalty_ledger",
            {"merchant_id": merchant_id, "customer_id": customer_id},
            columns="balance_after",
            order_by="created_at.desc",
        )

        current_balance = int(last["balance_after"]) if last else 0
        new_balance = current_balance + delta

        if preview:
            return {
                "ok": True,
                "preview": True,
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "event_type": event_type,
                "delta": delta,
                "balance_before": current_balance,
                "balance_after": new_balance,
            }

        row = {
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "event_type": event_type,
            "delta": delta,
            "balance_after": new_balance,
            "source": source,
            "metadata": metadata,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        insert_one("loyalty_ledger", row)

        return {
            "ok": True,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "event_type": event_type,
            "delta": delta,
            "balance_before": current_balance,
            "balance_after": new_balance,
        }

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"loyalty ledger error: {e}")
