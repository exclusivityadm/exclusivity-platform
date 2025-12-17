"""
Pricing Engine (Canonical)
=========================

Purpose:
- Recommend retail prices that maintain target margin while embedding:
  - program/platform fee
  - payment processing
  - rewards reserve (points)
  - optional overhead and risk buffers
  - optional shipping/ops/settlement allocations

Non-goals:
- This is not a discount engine.
- This avoids “crypto language” — points/badges only.

Works with cost_model.CostModel for consistent math.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any

from .cost_model import CostInputs, CostModel, D, _q2, _q4


@dataclass(frozen=True)
class PricingPolicy:
    """
    Merchant/store policy knobs.
    """

    target_net_margin: Decimal = D("0.35")  # desired net profit margin (after fees/reserves)
    rewards_rate_of_retail: Decimal = D("0.02")  # 2% of retail reserved for points
    platform_fee_rate: Decimal = D("0.0200")  # 2% program fee
    overhead_rate_of_retail: Decimal = D("0.00")
    risk_buffer_rate_of_retail: Decimal = D("0.00")

    payment_processor_rate: Decimal = D("0.029")
    payment_processor_fixed: Decimal = D("0.30")

    tax_rate: Decimal = D("0.00")

    # Order-level costs (allocated per unit via quantity)
    shipping_cost_per_order: Decimal = D("0.00")
    points_ops_cost_per_order: Decimal = D("0.00")
    settlement_cost_per_order: Decimal = D("0.00")

    # Rounding rules
    price_rounding: Decimal = D("0.01")  # currency cents
    psychological_pricing: bool = False  # if True, snap to *.99 where possible


@dataclass(frozen=True)
class PricingResult:
    retail_price: Decimal
    points_awarded: int
    cost_breakdown: Dict[str, str]
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retail_price": str(self.retail_price),
            "points_awarded": int(self.points_awarded),
            "cost_breakdown": self.cost_breakdown,
            "notes": self.notes,
        }


class PricingEngine:
    """
    Engine that solves for a retail price given:
    - unit COGS
    - policy rates and fixed costs
    - desired net margin

    Implementation:
    - Uses a numeric search for retail price because:
      fees/reserves include fixed components allocated per unit (processor fixed, shipping, ops, settlement).
    """

    def __init__(self, cost_model: Optional[CostModel] = None) -> None:
        self.cost_model = cost_model or CostModel()

    def recommend_price(
        self,
        *,
        unit_cost: Decimal,
        quantity: int = 1,
        policy: PricingPolicy,
        starting_price: Optional[Decimal] = None,
        max_iterations: int = 60,
    ) -> PricingResult:
        if quantity < 1:
            raise ValueError("quantity must be >= 1")
        if unit_cost < D("0.00"):
            raise ValueError("unit_cost must be >= 0")
        if not (D("0.00") <= policy.target_net_margin < D("1.00")):
            raise ValueError("target_net_margin must be between 0 and <1")

        # Reasonable starting guess:
        # If margin is 35% and we ignore fees/reserves, price ~ cost / (1-margin).
        # Then bump a bit for fees/reserves.
        if starting_price is None:
            base = unit_cost / (D("1.00") - policy.target_net_margin)
            starting_price = base * D("1.10")

        # Search bounds
        low = max(D("0.01"), unit_cost)  # price must at least cover cost generally
        high = max(starting_price * D("5.0"), low + D("1.00"))

        # Helper: compute margin at a price
        def margin_at(price: Decimal) -> Decimal:
            inputs = CostInputs(
                retail_price=price,
                unit_cost=unit_cost,
                quantity=quantity,
                payment_processor_rate=policy.payment_processor_rate,
                payment_processor_fixed=policy.payment_processor_fixed,
                platform_fee_rate=policy.platform_fee_rate,
                shipping_cost_per_order=policy.shipping_cost_per_order,
                tax_rate=policy.tax_rate,
                rewards_rate_of_retail=policy.rewards_rate_of_retail,
                points_ops_cost_per_order=policy.points_ops_cost_per_order,
                settlement_cost_per_order=policy.settlement_cost_per_order,
                overhead_rate_of_retail=policy.overhead_rate_of_retail,
                risk_buffer_rate_of_retail=policy.risk_buffer_rate_of_retail,
            )
            b = self.cost_model.compute(inputs)
            return D(b.net_margin)

        target = D(policy.target_net_margin)

        # Ensure high is high enough; expand if needed
        m_high = margin_at(high)
        expand_guard = 0
        while m_high < target and expand_guard < 8:
            high *= D("2.0")
            m_high = margin_at(high)
            expand_guard += 1

        # Binary search
        best = high
        for _ in range(max_iterations):
            mid = (low + high) / D("2.0")
            m_mid = margin_at(mid)
            if m_mid >= target:
                best = mid
                high = mid
            else:
                low = mid

        # Apply rounding + optional psychological pricing
        best = self._round_price(best, policy)

        # Final breakdown with rounded price
        final_inputs = CostInputs(
            retail_price=best,
            unit_cost=unit_cost,
            quantity=quantity,
            payment_processor_rate=policy.payment_processor_rate,
            payment_processor_fixed=policy.payment_processor_fixed,
            platform_fee_rate=policy.platform_fee_rate,
            shipping_cost_per_order=policy.shipping_cost_per_order,
            tax_rate=policy.tax_rate,
            rewards_rate_of_retail=policy.rewards_rate_of_retail,
            points_ops_cost_per_order=policy.points_ops_cost_per_order,
            settlement_cost_per_order=policy.settlement_cost_per_order,
            overhead_rate_of_retail=policy.overhead_rate_of_retail,
            risk_buffer_rate_of_retail=policy.risk_buffer_rate_of_retail,
        )
        breakdown = self.cost_model.compute(final_inputs)

        # Points model (canonical):
        # - Points are derived from rewards reserve in currency units.
        # - Conversion: 1 point = $0.01 by default (100 points = $1).
        rewards_value = D(breakdown.rewards_reserve)
        points = int((rewards_value / D("0.01")).to_integral_value(rounding=ROUND_HALF_UP))

        notes = (
            "Retail price computed to meet target net margin while embedding program fee, "
            "processing fees, and points reserve. Points are issued at 1 point = $0.01 of reserve."
        )

        return PricingResult(
            retail_price=_q2(best),
            points_awarded=points,
            cost_breakdown=breakdown.to_dict(),
            notes=notes,
        )

    def _round_price(self, price: Decimal, policy: PricingPolicy) -> Decimal:
        step = policy.price_rounding
        if step <= D("0.00"):
            return _q2(price)

        rounded = (price / step).to_integral_value(rounding=ROUND_HALF_UP) * step
        rounded = rounded.quantize(step, rounding=ROUND_HALF_UP)

        if policy.psychological_pricing:
            # Snap to *.99 if it doesn't undercut target too aggressively.
            # Keep it simple and stable:
            dollars = rounded.to_integral_value(rounding=ROUND_HALF_UP)
            candidate = dollars - D("0.01")
            if candidate > D("0.00"):
                return _q2(candidate)

        return _q2(rounded)
