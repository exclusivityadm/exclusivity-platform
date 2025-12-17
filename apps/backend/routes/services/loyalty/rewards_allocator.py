"""
Rewards Allocator (Canonical)
=============================

Purpose:
- Bridge pricing and order events to deterministic points issuance.
- Implements the "rewards baked into pricing" rule:
  points are derived from eligible spend * policy earn_rate_of_eligible_spend.

This module:
- Uses LoyaltyPolicy for the canonical points math
- Produces ledger events (but does NOT persist them)
- Supports partial refunds deterministically

No DB, no HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from .loyalty_policy import LoyaltyPolicy, D, _q2
from .points_ledger import LedgerEvent, PointsLedger


@dataclass(frozen=True)
class OrderLine:
    """
    Canonical order line input.

    All currency values are in store currency.
    """
    line_id: str
    product_id: Optional[str]
    title: str
    unit_price: Decimal
    quantity: int

    # Eligibility flags
    eligible_for_points: bool = True

    def line_subtotal(self) -> Decimal:
        qty = max(0, int(self.quantity))
        return Decimal(self.unit_price) * Decimal(qty)


@dataclass(frozen=True)
class OrderSnapshot:
    """
    Canonical order snapshot for issuing rewards.
    """
    order_id: str
    member_ref: str  # customer identifier (email mapping, etc.)

    lines: List[OrderLine]

    # Optional: if taxes/shipping should be excluded from eligible spend, omit them here
    # If included in line prices, they are implicitly included.
    currency: str = "USD"

    # Optional: global discount amount to exclude from eligible spend
    discounts_total: Decimal = D("0.00")


@dataclass(frozen=True)
class AllocationResult:
    eligible_spend: Decimal
    points_awarded: int
    events: List[LedgerEvent]
    explanation: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eligible_spend": str(_q2(self.eligible_spend)),
            "points_awarded": int(self.points_awarded),
            "events": [e.to_dict() for e in self.events],
            "explanation": self.explanation,
        }


class RewardsAllocator:
    """
    Canonical allocator for points issuance and refund adjustments.
    """

    def __init__(self, *, policy: LoyaltyPolicy, ledger: Optional[PointsLedger] = None) -> None:
        self.policy = policy
        self.ledger = ledger or PointsLedger(
            allow_negative_balance=policy.allow_negative_points_balance
        )

    # -----------------------------
    # Issuance
    # -----------------------------
    def allocate_for_order(
        self,
        *,
        order: OrderSnapshot,
        event_id_prefix: str,
        idempotency_prefix: str,
    ) -> AllocationResult:
        """
        Calculate eligible spend and points for an order, and return ledger events.

        This returns per-line events to support line-level refunds and auditing.
        """
        eligible_by_line: List[Tuple[OrderLine, Decimal]] = []
        for line in order.lines:
            if not line.eligible_for_points:
                eligible_by_line.append((line, D("0.00")))
                continue
            eligible_by_line.append((line, self._safe_money(line.line_subtotal())))

        eligible_total = sum((amt for _, amt in eligible_by_line), D("0.00"))

        # Apply discounts proportionally (excluding ineligible lines)
        discounts = self._safe_money(order.discounts_total)
        if discounts > D("0.00") and eligible_total > D("0.00"):
            eligible_by_line = self._apply_proportional_discounts(
                eligible_by_line, discounts_total=discounts, eligible_total=eligible_total
            )
            eligible_total = sum((amt for _, amt in eligible_by_line), D("0.00"))

        # Points calculated from total eligible spend via policy
        points_total = self.policy.points_for_eligible_spend(eligible_total)

        # Allocate points back to lines proportionally (to support refunds)
        per_line_points = self._allocate_points_to_lines(
            eligible_by_line=eligible_by_line,
            points_total=points_total,
        )

        # Create ledger events
        events: List[LedgerEvent] = []
        for line, pts in per_line_points:
            if pts <= 0:
                continue
            event_id = f"{event_id_prefix}:{order.order_id}:{line.line_id}"
            idem = f"{idempotency_prefix}:{order.order_id}:{line.line_id}"
            events.append(
                self.ledger.make_earn_event(
                    event_id=event_id,
                    member_ref=order.member_ref,
                    points=pts,
                    idempotency_key=idem,
                    order_id=order.order_id,
                    order_line_id=line.line_id,
                    meta={
                        "currency": order.currency,
                        "line_title": line.title,
                        "product_id": line.product_id,
                        "eligible_spend": str(_q2(self._line_eligible_amount(eligible_by_line, line.line_id))),
                        "policy_version": self.policy.version,
                    },
                )
            )

        explanation = {
            "rule": "Points are issued from eligible spend using the canonical loyalty policy.",
            "policy": self.policy.to_dict(),
            "eligible_spend_total": str(_q2(eligible_total)),
            "points_total": int(points_total),
            "line_points": [
                {
                    "line_id": line.line_id,
                    "title": line.title,
                    "eligible_spend": str(_q2(self._line_eligible_amount(eligible_by_line, line.line_id))),
                    "points": int(pts),
                }
                for line, pts in per_line_points
            ],
        }

        return AllocationResult(
            eligible_spend=_q2(eligible_total),
            points_awarded=int(points_total),
            events=events,
            explanation=explanation,
        )

    # -----------------------------
    # Refund / reversal
    # -----------------------------
    def allocate_refund_adjustment(
        self,
        *,
        order_id: str,
        refund_id: str,
        member_ref: str,
        original_earn_events: List[LedgerEvent],
        refund_line_amounts: Dict[str, Decimal],
        event_id_prefix: str,
        idempotency_prefix: str,
    ) -> List[LedgerEvent]:
        """
        Create refund events to remove points associated with refunded line amounts.

        Inputs:
        - original_earn_events: the earn events created for the original order (or loaded from DB)
        - refund_line_amounts: mapping of order_line_id -> refunded eligible amount (currency)

        Strategy:
        - Determine original eligible spend per line from earn event meta if present
          else fall back to proportional points removal based on points in earn events.
        - Convert refunded eligible amount to points using the policy, but clamp to the earned points for that line.
        """
        refund_events: List[LedgerEvent] = []

        # Map earned points per line
        earned_points_by_line: Dict[str, int] = {}
        eligible_spend_by_line: Dict[str, Decimal] = {}

        for e in original_earn_events:
            if e.event_type != "earn":
                continue
            line_id = e.related_line_ref
            if not line_id:
                continue
            earned_points_by_line[line_id] = earned_points_by_line.get(line_id, 0) + int(e.points_delta)

            # Try to read eligible spend from meta for better proportional refunds
            meta_amt = None
            if isinstance(e.meta, dict):
                meta_amt = e.meta.get("eligible_spend")
            if meta_amt is not None:
                try:
                    eligible_spend_by_line[line_id] = eligible_spend_by_line.get(line_id, D("0.00")) + D(str(meta_amt))
                except Exception:
                    pass

        for line_id, refunded_amt in refund_line_amounts.items():
            refunded_amt = self._safe_money(refunded_amt)
            if refunded_amt <= D("0.00"):
                continue

            earned_pts = int(earned_points_by_line.get(line_id, 0))
            if earned_pts <= 0:
                continue

            # Compute points to remove for refunded eligible amount
            # If we know original eligible spend, remove proportionally:
            if line_id in eligible_spend_by_line and eligible_spend_by_line[line_id] > D("0.00"):
                ratio = refunded_amt / eligible_spend_by_line[line_id]
                if ratio < D("0.00"):
                    ratio = D("0.00")
                if ratio > D("1.00"):
                    ratio = D("1.00")
                pts_to_remove = int(D(earned_pts) * ratio)
                if pts_to_remove <= 0:
                    # Minimum 1 point removal if there is any refunded amount and earned points exist
                    pts_to_remove = 1
            else:
                # Fallback: use policy conversion on refunded amount, clamp to earned
                pts_to_remove = self.policy.points_for_eligible_spend(refunded_amt)

            if pts_to_remove > earned_pts:
                pts_to_remove = earned_pts

            event_id = f"{event_id_prefix}:{refund_id}:{line_id}"
            idem = f"{idempotency_prefix}:{refund_id}:{line_id}"

            refund_events.append(
                self.ledger.make_refund_event(
                    event_id=event_id,
                    member_ref=member_ref,
                    points_to_remove=pts_to_remove,
                    idempotency_key=idem,
                    order_id=order_id,
                    refund_id=refund_id,
                    order_line_id=line_id,
                    meta={
                        "refunded_eligible_amount": str(_q2(refunded_amt)),
                        "earned_points_on_line": int(earned_pts),
                        "policy_version": self.policy.version,
                    },
                )
            )

        return refund_events

    # -----------------------------
    # Internal helpers
    # -----------------------------
    @staticmethod
    def _safe_money(v: Any) -> Decimal:
        try:
            x = Decimal(v)
        except Exception:
            x = D("0.00")
        if x < D("0.00"):
            x = D("0.00")
        return x

    @staticmethod
    def _apply_proportional_discounts(
        eligible_by_line: List[Tuple[OrderLine, Decimal]],
        *,
        discounts_total: Decimal,
        eligible_total: Decimal,
    ) -> List[Tuple[OrderLine, Decimal]]:
        """
        Reduce eligible spend by distributing discounts across eligible lines proportionally.
        """
        if discounts_total <= D("0.00") or eligible_total <= D("0.00"):
            return eligible_by_line

        adjusted: List[Tuple[OrderLine, Decimal]] = []
        remaining_discount = discounts_total

        # First pass proportional, second pass clamp
        for i, (line, amt) in enumerate(eligible_by_line):
            if amt <= D("0.00"):
                adjusted.append((line, amt))
                continue
            share = (amt / eligible_total) * discounts_total
            share = share if share <= remaining_discount else remaining_discount
            new_amt = amt - share
            if new_amt < D("0.00"):
                new_amt = D("0.00")
            adjusted.append((line, new_amt))
            remaining_discount -= share

        return adjusted

    @staticmethod
    def _allocate_points_to_lines(
        *,
        eligible_by_line: List[Tuple[OrderLine, Decimal]],
        points_total: int,
    ) -> List[Tuple[OrderLine, int]]:
        """
        Allocate points to lines proportional to eligible spend.
        Ensures total allocated equals points_total.
        """
        pts_total = max(0, int(points_total))
        if pts_total == 0:
            return [(line, 0) for line, _ in eligible_by_line]

        eligible_total = sum((amt for _, amt in eligible_by_line), D("0.00"))
        if eligible_total <= D("0.00"):
            return [(line, 0) for line, _ in eligible_by_line]

        # Initial allocation by proportion
        allocations: List[Tuple[OrderLine, int, Decimal]] = []
        allocated_sum = 0
        for line, amt in eligible_by_line:
            if amt <= D("0.00"):
                allocations.append((line, 0, D("0.00")))
                continue
            raw = (amt / eligible_total) * D(pts_total)
            pts = int(raw)  # floor for stable remainder handling
            allocations.append((line, pts, raw - D(pts)))
            allocated_sum += pts

        # Distribute remainders to highest fractional parts
        remainder = pts_total - allocated_sum
        if remainder > 0:
            # Sort by fractional remainder desc
            allocations_sorted = sorted(allocations, key=lambda x: x[2], reverse=True)
            for i in range(min(remainder, len(allocations_sorted))):
                line, pts, frac = allocations_sorted[i]
                allocations_sorted[i] = (line, pts + 1, frac)
            allocations = allocations_sorted

        # Return without fractional parts
        return [(line, pts) for (line, pts, _) in allocations]

    @staticmethod
    def _line_eligible_amount(
        eligible_by_line: List[Tuple[OrderLine, Decimal]],
        line_id: str,
    ) -> Decimal:
        for line, amt in eligible_by_line:
            if line.line_id == line_id:
                return amt
        return D("0.00")
