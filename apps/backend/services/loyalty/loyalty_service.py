"""
Loyalty Service (Canonical Integration Layer)
=============================================

Purpose:
- Orchestrate loyalty policy + tier engine + rewards allocator + points ledger
  with a repository (DB adapter).
- Keep routes thin. Keep domain logic in canonical modules.

This service:
- Loads merchant policy (or defaults)
- Computes member status (tier + points)
- Awards points for an order (per-line earn events)
- Applies refund adjustments (per-line removal events)
- Maintains lifetime spend and member snapshots through repository

No HTTP here. Routes should call this.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.services.loyalty.loyalty_policy import LoyaltyPolicy, D, _q2
from app.services.loyalty.tier_engine import TierEngine
from app.services.loyalty.points_ledger import PointsLedger, LedgerEvent
from app.services.loyalty.rewards_allocator import RewardsAllocator, OrderSnapshot, OrderLine

from app.repositories.loyalty_repository import LoyaltyRepository


@dataclass(frozen=True)
class MemberStatus:
    merchant_id: str
    member_ref: str
    lifetime_spend: Decimal
    tier: Dict[str, Any]
    next_tier: Optional[Dict[str, Any]]
    amount_to_next_tier: Optional[Decimal]
    points_balance: int
    points_earned_total: int
    points_removed_total: int
    policy_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merchant_id": self.merchant_id,
            "member_ref": self.member_ref,
            "lifetime_spend": str(_q2(self.lifetime_spend)),
            "tier": self.tier,
            "next_tier": self.next_tier,
            "amount_to_next_tier": None if self.amount_to_next_tier is None else str(_q2(self.amount_to_next_tier)),
            "points_balance": int(self.points_balance),
            "points_earned_total": int(self.points_earned_total),
            "points_removed_total": int(self.points_removed_total),
            "policy_version": self.policy_version,
        }


class LoyaltyService:
    """
    Canonical orchestration layer.

    Repo contract:
    - get_policy_json(merchant_id) -> dict|None
    - upsert_policy_json(merchant_id, policy_json) -> None
    - get_member_lifetime_spend(merchant_id, member_ref) -> Decimal
    - increment_member_lifetime_spend(merchant_id, member_ref, amount) -> Decimal (returns new total)
    - list_ledger_events(merchant_id, member_ref) -> List[LedgerEvent]
    - append_ledger_events(merchant_id, events) -> Dict (result)
    """

    def __init__(self, repo: LoyaltyRepository) -> None:
        self.repo = repo

    # -----------------------------
    # Policy
    # -----------------------------
    async def get_policy(self, merchant_id: str) -> LoyaltyPolicy:
        data = await self.repo.get_policy_json(merchant_id)
        if isinstance(data, dict) and data:
            return LoyaltyPolicy.from_dict(data)
        return LoyaltyPolicy()

    async def upsert_policy(self, merchant_id: str, policy_dict: Dict[str, Any]) -> LoyaltyPolicy:
        policy = LoyaltyPolicy.from_dict(policy_dict or {})
        await self.repo.upsert_policy_json(merchant_id, policy.to_dict())
        return policy

    # -----------------------------
    # Member status
    # -----------------------------
    async def get_member_status(self, merchant_id: str, member_ref: str) -> MemberStatus:
        policy = await self.get_policy(merchant_id)

        lifetime_spend = await self.repo.get_member_lifetime_spend(merchant_id, member_ref)
        lifetime_spend = Decimal(lifetime_spend or D("0.00"))
        if lifetime_spend < D("0.00"):
            lifetime_spend = D("0.00")

        tier_engine = TierEngine(policy)
        status = tier_engine.evaluate(lifetime_spend)

        events = await self.repo.list_ledger_events(merchant_id, member_ref)
        ledger = PointsLedger(allow_negative_balance=policy.allow_negative_points_balance)
        ledger_state = ledger.reduce(member_ref, events)

        nxt = status.next_tier
        return MemberStatus(
            merchant_id=merchant_id,
            member_ref=member_ref,
            lifetime_spend=_q2(lifetime_spend),
            tier={"key": status.current_tier.key, "name": status.current_tier.name},
            next_tier=None if nxt is None else {"key": nxt.key, "name": nxt.name},
            amount_to_next_tier=status.amount_to_next_tier,
            points_balance=ledger_state.points_balance,
            points_earned_total=ledger_state.total_earned,
            points_removed_total=ledger_state.total_spent_or_removed,
            policy_version=policy.version,
        )

    # -----------------------------
    # Award points (order)
    # -----------------------------
    async def award_for_order(
        self,
        *,
        merchant_id: str,
        order_id: str,
        member_ref: str,
        lines: List[Dict[str, Any]],
        discounts_total: Decimal = D("0.00"),
        currency: str = "USD",
        # deterministic keys:
        event_id_prefix: str = "earn",
        idempotency_prefix: str = "idem:earn",
        # lifetime spend:
        lifetime_spend_increment: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Award points for a completed order.

        - Creates per-line earn events (idempotent by order_id+line_id)
        - Appends events via repo
        - Updates lifetime spend by either:
            a) explicit lifetime_spend_increment (recommended)
            b) derived eligible spend total (fallback)

        Returns a structured payload for routes/admin/ai logs.
        """
        policy = await self.get_policy(merchant_id)

        order_lines = [self._parse_line(x) for x in (lines or [])]
        order = OrderSnapshot(
            order_id=order_id,
            member_ref=member_ref,
            lines=order_lines,
            currency=currency,
            discounts_total=Decimal(discounts_total or D("0.00")),
        )

        allocator = RewardsAllocator(policy=policy)
        allocation = allocator.allocate_for_order(
            order=order,
            event_id_prefix=event_id_prefix,
            idempotency_prefix=idempotency_prefix,
        )

        # Persist events
        append_result = await self.repo.append_ledger_events(merchant_id, allocation.events)

        # Update lifetime spend
        if lifetime_spend_increment is None:
            # fallback to eligible spend (keeps tiering consistent with spend)
            lifetime_spend_increment = allocation.eligible_spend

        new_total = await self.repo.increment_member_lifetime_spend(
            merchant_id=merchant_id,
            member_ref=member_ref,
            amount=Decimal(lifetime_spend_increment or D("0.00")),
        )

        # Return post-status snapshot
        member_status = await self.get_member_status(merchant_id, member_ref)

        return {
            "ok": True,
            "merchant_id": merchant_id,
            "order_id": order_id,
            "member_ref": member_ref,
            "awarded_points_total": int(allocation.points_awarded),
            "eligible_spend": str(_q2(allocation.eligible_spend)),
            "events_written": len(allocation.events),
            "append_result": append_result,
            "lifetime_spend_increment": str(_q2(Decimal(lifetime_spend_increment or D("0.00")))),
            "lifetime_spend_total": str(_q2(Decimal(new_total or D("0.00")))),
            "policy_version": policy.version,
            "member_status": member_status.to_dict(),
            "explanation": allocation.explanation,
        }

    # -----------------------------
    # Refund adjustment
    # -----------------------------
    async def adjust_for_refund(
        self,
        *,
        merchant_id: str,
        order_id: str,
        refund_id: str,
        member_ref: str,
        refund_line_amounts: Dict[str, Any],  # line_id -> refunded eligible amount
        # deterministic keys:
        event_id_prefix: str = "refund",
        idempotency_prefix: str = "idem:refund",
        # optional: decrease lifetime spend? default False for lifetime spend programs
        decrement_lifetime_spend: bool = False,
    ) -> Dict[str, Any]:
        """
        Apply refund adjustments:
        - Looks up original earn events for the order (via repo)
        - Computes per-line points removal events (idempotent by refund_id+line_id)
        - Appends refund events
        - Optionally adjusts lifetime spend (default: no, because lifetime spend is lifetime)
        """
        policy = await self.get_policy(merchant_id)

        original_earn_events = await self.repo.list_order_earn_events(
            merchant_id=merchant_id,
            member_ref=member_ref,
            order_id=order_id,
        )

        # Normalize refund_line_amounts
        norm: Dict[str, Decimal] = {}
        for k, v in (refund_line_amounts or {}).items():
            try:
                norm[str(k)] = Decimal(v)
            except Exception:
                norm[str(k)] = D("0.00")

        allocator = RewardsAllocator(policy=policy)
        refund_events = allocator.allocate_refund_adjustment(
            order_id=order_id,
            refund_id=refund_id,
            member_ref=member_ref,
            original_earn_events=original_earn_events,
            refund_line_amounts=norm,
            event_id_prefix=event_id_prefix,
            idempotency_prefix=idempotency_prefix,
        )

        append_result = await self.repo.append_ledger_events(merchant_id, refund_events)

        spend_delta = D("0.00")
        if decrement_lifetime_spend:
            # Not recommended for lifetime-spend tiering, but supported as an explicit choice.
            spend_delta = -sum((x for x in norm.values()), D("0.00"))
            await self.repo.increment_member_lifetime_spend(merchant_id, member_ref, spend_delta)

        member_status = await self.get_member_status(merchant_id, member_ref)

        removed_total = sum((abs(int(e.points_delta)) for e in refund_events), 0)

        return {
            "ok": True,
            "merchant_id": merchant_id,
            "order_id": order_id,
            "refund_id": refund_id,
            "member_ref": member_ref,
            "refund_events_written": len(refund_events),
            "points_removed_total": int(removed_total),
            "append_result": append_result,
            "lifetime_spend_delta": str(_q2(spend_delta)),
            "policy_version": policy.version,
            "member_status": member_status.to_dict(),
        }

    # -----------------------------
    # Helpers
    # -----------------------------
    @staticmethod
    def _parse_line(x: Dict[str, Any]) -> OrderLine:
        return OrderLine(
            line_id=str(x.get("line_id") or x.get("id") or ""),
            product_id=(str(x.get("product_id")) if x.get("product_id") is not None else None),
            title=str(x.get("title") or x.get("name") or "Item"),
            unit_price=Decimal(x.get("unit_price") or x.get("price") or D("0.00")),
            quantity=int(x.get("quantity") or 1),
            eligible_for_points=bool(x.get("eligible_for_points", True)),
        )
