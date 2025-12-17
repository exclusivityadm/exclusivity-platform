from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List


# -------------------------------------------------
# Ledger domain model (REQUIRED by loyalty repo)
# -------------------------------------------------
@dataclass
class LedgerEvent:
    event_id: str
    member_ref: str
    event_type: str
    points_delta: int
    created_at: str

    idempotency_key: Optional[str] = None
    related_ref: Optional[str] = None
    related_line_ref: Optional[str] = None
    reason: Optional[str] = None
    meta: Dict[str, Any] | None = None


# -------------------------------------------------
# Existing helper functions (UNCHANGED)
# -------------------------------------------------
def add_points(supa, merchant_id, customer_id, delta, reason, ref=None):
    supa.table("points_ledger").insert(
        {
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "delta": int(delta),
            "reason": reason,
            "ref": ref or {},
        }
    ).execute()


def total_points(supa, merchant_id, customer_id):
    try:
        res = supa.rpc("sum_points", {"m": merchant_id, "c": customer_id}).execute()
        if res and res.data:
            return int(res.data[0].get("sum") or 0)
    except Exception:
        pass

    rows = (
        supa.table("points_ledger")
        .select("delta")
        .eq("merchant_id", merchant_id)
        .eq("customer_id", customer_id)
        .execute()
        .data
        or []
    )
    return sum(int(r["delta"]) for r in rows)
