"""
Tier Engine (Canonical)
======================

Purpose:
- Deterministic tier computation based ONLY on lifetime spend.
- No side effects, no DB access, no HTTP.
- Produces explanation payloads suitable for AI, admin dashboards, and audits.

This engine strictly enforces:
- Non-punitive behavior (no forced downgrades).
- Lifetime-spend-only progression.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Any, Optional

from .loyalty_policy import LoyaltyPolicy, Tier, D, _q2


@dataclass(frozen=True)
class TierStatus:
    """
    Snapshot of a member's tier position.
    """
    current_tier: Tier
    lifetime_spend: Decimal
    next_tier: Optional[Tier]
    amount_to_next_tier: Optional[Decimal]
    is_top_tier: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_tier": {
                "key": self.current_tier.key,
                "name": self.current_tier.name,
                "min_lifetime_spend": str(_q2(self.current_tier.min_lifetime_spend)),
            },
            "lifetime_spend": str(_q2(self.lifetime_spend)),
            "next_tier": None
            if self.next_tier is None
            else {
                "key": self.next_tier.key,
                "name": self.next_tier.name,
                "min_lifetime_spend": str(_q2(self.next_tier.min_lifetime_spend)),
            },
            "amount_to_next_tier": None
            if self.amount_to_next_tier is None
            else str(_q2(self.amount_to_next_tier)),
            "is_top_tier": self.is_top_tier,
        }


class TierEngine:
    """
    Canonical tier computation engine.
    """

    def __init__(self, policy: LoyaltyPolicy) -> None:
        self.policy = policy

    # -----------------------------
    # Core evaluation
    # -----------------------------
    def evaluate(self, lifetime_spend: Decimal) -> TierStatus:
        """
        Compute tier status for a given lifetime spend amount.
        """
        spend = self._normalize_spend(lifetime_spend)

        current = self.policy.tier_for_lifetime_spend(spend)
        next_tier = self.policy.next_tier(spend)
        remaining = self.policy.amount_to_next_tier(spend)

        is_top = next_tier is None

        return TierStatus(
            current_tier=current,
            lifetime_spend=_q2(spend),
            next_tier=next_tier,
            amount_to_next_tier=remaining,
            is_top_tier=is_top,
        )

    # -----------------------------
    # Advancement logic
    # -----------------------------
    def would_advance_with_purchase(
        self,
        *,
        lifetime_spend: Decimal,
        purchase_amount: Decimal,
    ) -> Dict[str, Any]:
        """
        Determine whether a hypothetical purchase would advance the tier.

        This is used for:
        - AI explanations ("this purchase would move you to Gold")
        - Admin previews
        - Merchant UX nudges (non-coercive)

        No state mutation.
        """
        spend = self._normalize_spend(lifetime_spend)
        purchase = max(D("0.00"), Decimal(purchase_amount))

        before = self.evaluate(spend)
        after_spend = spend + purchase
        after = self.evaluate(after_spend)

        advanced = before.current_tier.key != after.current_tier.key

        return {
            "advanced": advanced,
            "before": before.to_dict(),
            "after": after.to_dict(),
            "explanation": self._advance_explanation(
                advanced=advanced,
                before=before,
                after=after,
                purchase_amount=purchase,
            ),
        }

    # -----------------------------
    # Downgrade handling (explicitly constrained)
    # -----------------------------
    def downgrade_check(
        self,
        *,
        lifetime_spend_before: Decimal,
        lifetime_spend_after: Decimal,
    ) -> Dict[str, Any]:
        """
        Evaluate whether a downgrade *would* occur and how the system handles it.

        By default:
        - Downgrades are not applied (lifetime-spend programs).
        - This function exists for transparency and audits only.
        """
        before = self.evaluate(lifetime_spend_before)
        after = self.evaluate(lifetime_spend_after)

        downgrade_detected = (
            after.current_tier.min_lifetime_spend
            < before.current_tier.min_lifetime_spend
        )

        if downgrade_detected and not self.policy.allow_downgrades:
            return {
                "downgrade_detected": True,
                "applied": False,
                "reason": "Downgrades are disabled for lifetime-spend programs.",
                "retained_tier": before.current_tier.key,
            }

        return {
            "downgrade_detected": downgrade_detected,
            "applied": downgrade_detected,
            "new_tier": after.current_tier.key if downgrade_detected else before.current_tier.key,
        }

    # -----------------------------
    # Explanation helpers
    # -----------------------------
    def explain_status(self, lifetime_spend: Decimal) -> Dict[str, Any]:
        """
        Plain-language explanation payload for AI and admin UIs.
        """
        status = self.evaluate(lifetime_spend)

        if status.is_top_tier:
            message = (
                f"You are in the highest tier ({status.current_tier.name}). "
                "There is no higher tier to reach."
            )
        else:
            message = (
                f"You are currently in the {status.current_tier.name} tier. "
                f"Spend {status.amount_to_next_tier} more in lifetime purchases "
                f"to reach {status.next_tier.name}."
            )

        return {
            "tier_status": status.to_dict(),
            "message": message,
            "rule": "Tiers are determined only by lifetime spend.",
            "non_punitive": True,
        }

    def _advance_explanation(
        self,
        *,
        advanced: bool,
        before: TierStatus,
        after: TierStatus,
        purchase_amount: Decimal,
    ) -> str:
        if advanced:
            return (
                f"A purchase of {str(_q2(purchase_amount))} would move the member "
                f"from {before.current_tier.name} to {after.current_tier.name}."
            )
        if before.is_top_tier:
            return (
                f"The member is already in the highest tier ({before.current_tier.name}). "
                "No further tier advancement is possible."
            )
        return (
            f"A purchase of {str(_q2(purchase_amount))} would not yet advance the tier. "
            f"{before.amount_to_next_tier} in additional lifetime spend is still needed "
            f"to reach {before.next_tier.name}."
        )

    # -----------------------------
    # Utilities
    # -----------------------------
    @staticmethod
    def _normalize_spend(value: Decimal) -> Decimal:
        try:
            spend = Decimal(value)
        except Exception:
            spend = D("0.00")
        if spend < D("0.00"):
            spend = D("0.00")
        return spend
