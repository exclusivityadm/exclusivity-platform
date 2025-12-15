from __future__ import annotations

import os
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ..services.points import LedgerEvent


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
        r = (
            self.sb.table(self.table_policies)
            .select("policy")
            .eq("merchant_id", merchant_id)
            .maybe_single()
            .execute()
        )
        data = getattr(r, "data", None)
        return data.get("policy") if isinstance(data, dict) else None

    async def upsert_policy_json(self, merchant_id: str, policy_json: Dict[str, Any]) -> None:
        self.sb.table(self.table_policies).upsert(
            {"merchant_id": merchant_id, "policy": policy_json}
        ).execute()

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
        return Decimal(str(data.get("lifetime_spend", "0.00"))) if isinstance(data, dict) else Decimal("0.00")

    async def increment_member_lifetime_spend(
        self, merchant_id: str, member_ref: str, amount: Decimal
    ) -> Decimal:
        current = await self.get_member_lifetime_spend(merchant_id, member_ref)
        new_total = max(Decimal("0.00"), current + Decimal(amount or 0))
        self.sb.table(self.table_members).upsert(
            {"merchant_id": merchant_id, "member_ref": member_ref, "lifetime_spend": str(new_total)}
        ).execute()
        return new_total

    # -----------------------------
    # Ledger
    # -----------------------------
    async def list_ledger_events(self, merchant_id: str, member_ref: str) -> List[LedgerEvent]:
        r = (
            self.sb.table(self.table_events)
            .select("*")
            .eq("merchant_id", merchant_id)
            .eq("member_ref", member_ref)
            .order("created_at")
            .execute()
        )
        rows = getattr(r, "data", None) or []
        return [self._row_to_event(row) for row in rows if isinstance(row, dict)]

    async def append_ledger_events(
        self, merchant_id: str, events: List[LedgerEvent]
    ) -> Dict[str, Any]:
        if not events:
            return {"inserted": 0}

        payload = [
            {
                "merchant_id": merchant_id,
                "event_id": e.event_id,
                "member_ref": e.member_ref,
                "event_type": e.event_type,
                "points_delta": e.points_delta,
                "idempotency_key": e.idempotency_key,
                "related_ref": e.related_ref,
                "related_line_ref": e.related_line_ref,
                "created_at": e.created_at,
                "reason": e.reason,
                "meta": e.meta or {},
            }
            for e in events
        ]

        r = self.sb.table(self.table_events).insert(payload).execute()
        return {"inserted": len(getattr(r, "data", None) or [])}

    @staticmethod
    def _row_to_event(row: Dict[str, Any]) -> LedgerEvent:
        return LedgerEvent(
            event_id=str(row["event_id"]),
            member_ref=str(row["member_ref"]),
            event_type=str(row["event_type"]),
            points_delta=int(row["points_delta"]),
            idempotency_key=row.get("idempotency_key"),
            related_ref=row.get("related_ref"),
            related_line_ref=row.get("related_line_ref"),
            created_at=str(row.get("created_at")),
            reason=row.get("reason"),
            meta=row.get("meta") or {},
        )


def create_supabase_client_from_env() -> Any:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()
    if not url or not key:
        raise RuntimeError("Supabase env vars not set")

    from supabase import create_client  # type: ignore
    return create_client(url, key)
