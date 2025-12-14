"""
Loyalty Repository (Supabase/Postgres Adapter)
==============================================

Purpose:
- DB-facing adapter for loyalty policy, member spend, and points ledger events.
- Designed to work with supabase-py style client, BUT remains generic.

Expected tables (recommended canonical names):
1) public.loyalty_policies
   - merchant_id text primary key
   - policy jsonb not null
   - updated_at timestamptz default now()

2) public.loyalty_members
   - merchant_id text
   - member_ref text
   - lifetime_spend numeric default 0
   - created_at timestamptz default now()
   - updated_at timestamptz default now()
   PRIMARY KEY (merchant_id, member_ref)

3) public.loyalty_ledger_events
   - merchant_id text
   - event_id text primary key
   - member_ref text
   - event_type text
   - points_delta int
   - idempotency_key text unique null
   - related_ref text null
   - related_line_ref text null
   - created_at timestamptz default now()
   - reason text null
   - meta jsonb default '{}'::jsonb

You can rename tables later, but keep repo centralized to avoid drift.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.services.loyalty.points_ledger import LedgerEvent


class LoyaltyRepository:
    def __init__(
        self,
        supabase_client: Any,
        *,
        table_policies: str = "loyalty_policies",
        table_members: str = "loyalty_members",
        table_events: str = "loyalty_ledger_events",
    ) -> None:
        self.sb = supabase_client
        self.table_policies = table_policies
        self.table_members = table_members
        self.table_events = table_events

    # -----------------------------
    # Policy
    # -----------------------------
    async def get_policy_json(self, merchant_id: str) -> Optional[Dict[str, Any]]:
        r = self.sb.table(self.table_policies).select("policy").eq("merchant_id", merchant_id).maybe_single().execute()
        data = getattr(r, "data", None)
        if not data:
            return None
        # supabase-py maybe_single returns dict
        if isinstance(data, dict) and "policy" in data:
            return data["policy"]
        # sometimes returns list
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return data[0].get("policy")
        return None

    async def upsert_policy_json(self, merchant_id: str, policy_json: Dict[str, Any]) -> None:
        payload = {"merchant_id": merchant_id, "policy": policy_json}
        self.sb.table(self.table_policies).upsert(payload).execute()

    # -----------------------------
    # Member spend
    # -----------------------------
    async def get_member_lifetime_spend(self, merchant_id: str, member_ref: str) -> Decimal:
        r = (
            self.sb.table(self.table_members)
            .select("lifetime_spend")
            .eq("merchant_id", merchant_id)
            .eq("member_ref", member_ref)
            .maybe_single()
            .execute()
        )
        data = getattr(r, "data", None)
        if not data:
            return Decimal("0.00")
        if isinstance(data, dict):
            return Decimal(str(data.get("lifetime_spend", "0.00")))
        if isinstance(data, list) and len(data) > 0:
            return Decimal(str(data[0].get("lifetime_spend", "0.00")))
        return Decimal("0.00")

    async def increment_member_lifetime_spend(self, merchant_id: str, member_ref: str, amount: Decimal) -> Decimal:
        """
        Upsert member and increment lifetime_spend.
        Uses a read-modify-write approach for portability.
        If you want stronger concurrency guarantees, replace with an RPC.
        """
        amount = Decimal(amount or Decimal("0.00"))
        current = await self.get_member_lifetime_spend(merchant_id, member_ref)
        new_total = current + amount

        if new_total < Decimal("0.00"):
            new_total = Decimal("0.00")

        payload = {
            "merchant_id": merchant_id,
            "member_ref": member_ref,
            "lifetime_spend": str(new_total),
        }
        self.sb.table(self.table_members).upsert(payload).execute()
        return new_total

    # -----------------------------
    # Ledger events
    # -----------------------------
    async def list_ledger_events(self, merchant_id: str, member_ref: str) -> List[LedgerEvent]:
        r = (
            self.sb.table(self.table_events)
            .select("*")
            .eq("merchant_id", merchant_id)
            .eq("member_ref", member_ref)
            .order("created_at", desc=False)
            .execute()
        )
        rows = getattr(r, "data", None) or []
        events: List[LedgerEvent] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            events.append(self._row_to_event(row))
        return events

    async def list_order_earn_events(self, merchant_id: str, member_ref: str, order_id: str) -> List[LedgerEvent]:
        """
        Fetch earn events for an order.
        We key off related_ref = order_id (as created by RewardsAllocator).
        """
        r = (
            self.sb.table(self.table_events)
            .select("*")
            .eq("merchant_id", merchant_id)
            .eq("member_ref", member_ref)
            .eq("event_type", "earn")
            .eq("related_ref", order_id)
            .execute()
        )
        rows = getattr(r, "data", None) or []
        return [self._row_to_event(x) for x in rows if isinstance(x, dict)]

    async def append_ledger_events(self, merchant_id: str, events: List[LedgerEvent]) -> Dict[str, Any]:
        """
        Insert events. Idempotency should be enforced by unique constraints on event_id and/or idempotency_key.
        """
        if not events:
            return {"inserted": 0, "skipped": 0}

        payload = []
        for e in events:
            payload.append(
                {
                    "merchant_id": merchant_id,
                    "event_id": e.event_id,
                    "member_ref": e.member_ref,
                    "event_type": e.event_type,
                    "points_delta": int(e.points_delta),
                    "idempotency_key": e.idempotency_key,
                    "related_ref": e.related_ref,
                    "related_line_ref": e.related_line_ref,
                    "created_at": e.created_at,
                    "reason": e.reason,
                    "meta": e.meta or {},
                }
            )

        try:
            r = self.sb.table(self.table_events).insert(payload).execute()
            inserted = len(getattr(r, "data", None) or [])
            return {"inserted": inserted, "attempted": len(payload)}
        except Exception as ex:
            # In production, you may want to parse conflict errors and return structured info.
            return {"inserted": 0, "attempted": len(payload), "error": str(ex)}

    # -----------------------------
    # Row mapping
    # -----------------------------
    @staticmethod
    def _row_to_event(row: Dict[str, Any]) -> LedgerEvent:
        return LedgerEvent(
            event_id=str(row.get("event_id")),
            member_ref=str(row.get("member_ref")),
            event_type=str(row.get("event_type")),
            points_delta=int(row.get("points_delta", 0)),
            idempotency_key=row.get("idempotency_key"),
            related_ref=row.get("related_ref"),
            related_line_ref=row.get("related_line_ref"),
            created_at=str(row.get("created_at") or ""),
            reason=row.get("reason"),
            meta=row.get("meta") if isinstance(row.get("meta"), dict) else {},
        )


# ---------------------------------------
# Optional: minimal supabase client factory
# ---------------------------------------
def create_supabase_client_from_env() -> Any:
    """
    Convenience factory to create a Supabase client from env vars.
    This keeps routes/services structurally complete even before your DI wiring is finalized.

    Requires env:
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY

    If supabase library is not installed, raises a clear error.
    """
    url = os.getenv("SUPABASE_URL", "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()

    if not url or not key:
        raise RuntimeError("Supabase not configured: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY).")

    try:
        from supabase import create_client  # type: ignore
    except Exception as e:
        raise RuntimeError("supabase client library not installed. Install supabase-py.") from e

    return create_client(url, key)
