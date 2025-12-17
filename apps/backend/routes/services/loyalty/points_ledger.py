"""
Points Ledger (Canonical)
=========================

Purpose:
- Deterministic points balance math with idempotency support.
- Pure domain logic: no DB, no HTTP.
- Handles earn, adjust (refund/correction), and admin adjustments.
- Enforces non-punitive constraints (optionally disallow negative balances).

Design:
- LedgerEvent is an immutable record (in DB you store it; here we model it).
- Balance is computed by reducing events (stable and auditable).
- Idempotency keys prevent double-application when upstream retries occur.

Notes:
- This module does not decide HOW MANY points to issue for spend.
  That is handled by rewards_allocator.py and loyalty_policy.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Literal, Set, Tuple


EventType = Literal[
    "earn",
    "refund",
    "correction",
    "admin_grant",
    "admin_revoke",
]


def _now_utc_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass(frozen=True)
class LedgerEvent:
    """
    Immutable event record.
    points_delta:
        + positive => increase balance
        + negative => decrease balance
    """
    event_id: str
    member_ref: str  # customer identifier (email mapping, etc.)
    event_type: EventType
    points_delta: int

    # Idempotency and linking
    idempotency_key: Optional[str] = None  # stable key for retries
    related_ref: Optional[str] = None      # e.g., order_id, refund_id, adjustment_id
    related_line_ref: Optional[str] = None # e.g., order_line_id for per-line issuance

    # Metadata
    created_at: str = field(default_factory=_now_utc_iso)
    reason: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "member_ref": self.member_ref,
            "event_type": self.event_type,
            "points_delta": int(self.points_delta),
            "idempotency_key": self.idempotency_key,
            "related_ref": self.related_ref,
            "related_line_ref": self.related_line_ref,
            "created_at": self.created_at,
            "reason": self.reason,
            "meta": self.meta,
        }


@dataclass(frozen=True)
class LedgerState:
    """
    Computed state from a set of events.
    """
    member_ref: str
    points_balance: int
    total_earned: int
    total_spent_or_removed: int
    applied_event_ids: List[str]
    applied_idempotency_keys: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "member_ref": self.member_ref,
            "points_balance": int(self.points_balance),
            "total_earned": int(self.total_earned),
            "total_spent_or_removed": int(self.total_spent_or_removed),
            "applied_event_ids": self.applied_event_ids,
            "applied_idempotency_keys": self.applied_idempotency_keys,
        }


class PointsLedger:
    """
    Canonical ledger reducer and validation.

    The DB layer should store events and can use this module to:
    - validate new events
    - compute balances deterministically
    - enforce idempotency rules
    """

    def __init__(self, *, allow_negative_balance: bool = False) -> None:
        self.allow_negative_balance = bool(allow_negative_balance)

    # -----------------------------
    # Reduce / compute
    # -----------------------------
    def reduce(self, member_ref: str, events: Iterable[LedgerEvent]) -> LedgerState:
        """
        Compute balance and rollups for the provided events.
        Applies idempotency: duplicates by event_id or idempotency_key are ignored.
        """
        applied_event_ids: Set[str] = set()
        applied_idem: Set[str] = set()

        balance = 0
        total_earned = 0
        total_removed = 0

        # Stable ordering: by created_at then event_id
        ordered = sorted(list(events), key=lambda e: (e.created_at, e.event_id))

        for e in ordered:
            if e.member_ref != member_ref:
                continue

            if e.event_id in applied_event_ids:
                continue

            if e.idempotency_key and e.idempotency_key in applied_idem:
                continue

            # Apply
            balance += int(e.points_delta)
            if int(e.points_delta) >= 0:
                total_earned += int(e.points_delta)
            else:
                total_removed += abs(int(e.points_delta))

            applied_event_ids.add(e.event_id)
            if e.idempotency_key:
                applied_idem.add(e.idempotency_key)

        if not self.allow_negative_balance and balance < 0:
            # Non-punitive: clamp at 0 rather than punishing with negative debt.
            balance = 0

        return LedgerState(
            member_ref=member_ref,
            points_balance=int(balance),
            total_earned=int(total_earned),
            total_spent_or_removed=int(total_removed),
            applied_event_ids=sorted(list(applied_event_ids)),
            applied_idempotency_keys=sorted(list(applied_idem)),
        )

    # -----------------------------
    # Validation helpers
    # -----------------------------
    def validate_new_event(
        self,
        *,
        member_ref: str,
        existing_events: Iterable[LedgerEvent],
        new_event: LedgerEvent,
    ) -> Dict[str, Any]:
        """
        Validate whether a new event can be appended safely.

        Returns a structured result instead of raising in most cases
        to support cooperative handling upstream.
        """
        if new_event.member_ref != member_ref:
            return {
                "ok": False,
                "error": "member_ref mismatch",
                "code": "MEMBER_MISMATCH",
            }

        if new_event.points_delta == 0:
            return {
                "ok": False,
                "error": "points_delta cannot be 0",
                "code": "ZERO_DELTA",
            }

        # Idempotency check
        existing_ids = {e.event_id for e in existing_events if e.member_ref == member_ref}
        if new_event.event_id in existing_ids:
            return {
                "ok": False,
                "error": "duplicate event_id",
                "code": "DUP_EVENT_ID",
            }

        if new_event.idempotency_key:
            existing_idem = {
                e.idempotency_key
                for e in existing_events
                if e.member_ref == member_ref and e.idempotency_key
            }
            if new_event.idempotency_key in existing_idem:
                return {
                    "ok": False,
                    "error": "duplicate idempotency_key",
                    "code": "DUP_IDEMPOTENCY",
                }

        # Negative balance policy
        if not self.allow_negative_balance and new_event.points_delta < 0:
            state = self.reduce(member_ref, existing_events)
            projected = state.points_balance + int(new_event.points_delta)
            if projected < 0:
                return {
                    "ok": True,
                    "warning": "event would drive balance below 0; ledger clamps to 0",
                    "code": "CLAMP_TO_ZERO",
                    "projected_balance": projected,
                    "effective_balance_after_clamp": 0,
                }

        return {"ok": True}

    # -----------------------------
    # Event constructors (optional)
    # -----------------------------
    def make_earn_event(
        self,
        *,
        event_id: str,
        member_ref: str,
        points: int,
        idempotency_key: str,
        order_id: str,
        order_line_id: Optional[str] = None,
        reason: str = "Earned points from eligible spend",
        meta: Optional[Dict[str, Any]] = None,
    ) -> LedgerEvent:
        return LedgerEvent(
            event_id=event_id,
            member_ref=member_ref,
            event_type="earn",
            points_delta=max(0, int(points)),
            idempotency_key=idempotency_key,
            related_ref=order_id,
            related_line_ref=order_line_id,
            reason=reason,
            meta=meta or {},
        )

    def make_refund_event(
        self,
        *,
        event_id: str,
        member_ref: str,
        points_to_remove: int,
        idempotency_key: str,
        order_id: str,
        refund_id: str,
        order_line_id: Optional[str] = None,
        reason: str = "Refund adjustment",
        meta: Optional[Dict[str, Any]] = None,
    ) -> LedgerEvent:
        return LedgerEvent(
            event_id=event_id,
            member_ref=member_ref,
            event_type="refund",
            points_delta=-abs(int(points_to_remove)),
            idempotency_key=idempotency_key,
            related_ref=refund_id or order_id,
            related_line_ref=order_line_id,
            reason=reason,
            meta={"order_id": order_id, **(meta or {})},
        )
