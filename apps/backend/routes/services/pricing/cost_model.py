"""
Cost Model (Canonical)
======================

Purpose:
- Provide a deterministic, auditable, merchant-friendly cost breakdown for any order or item.
- Support "rewards baked into pricing" (loyalty is not a separate coupon system).
- Avoid crypto terms; use "points" and "badges" language (chain is implementation detail).

Design notes:
- This module is pure-business-logic: no DB, no HTTP.
- It is used by pricing_engine.py and can also be called by admin tooling / analytics.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional


D = Decimal


def _q2(x: Decimal) -> Decimal:
    """Quantize to 2 decimals like currency."""
    return x.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def _q4(x: Decimal) -> Decimal:
    """Quantize to 4 decimals for rates."""
    return x.quantize(D("0.0001"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CostInputs:
    """
    Inputs describing the economics of a single unit / line item.

    All currency fields are in the store currency (USD typically).
    Rates are decimals: 0.029 for 2.9%, etc.
    """

    # Core price inputs
    retail_price: Decimal  # customer-facing price (per unit)
    unit_cost: Decimal  # COGS per unit
    quantity: int = 1

    # Processor fees (e.g., Stripe)
    payment_processor_rate: Decimal = D("0.029")
    payment_processor_fixed: Decimal = D("0.30")  # fixed per order, allocated per unit via quantity

    # Platform fee (your program fee, “developer fee”, etc.)
    platform_fee_rate: Decimal = D("0.0200")  # 2% default

    # Optional: shipping and taxes can be modeled outside or passed in
    shipping_cost_per_order: Decimal = D("0.00")
    tax_rate: Decimal = D("0.00")  # if taxes are included in price, set appropriately

    # Rewards baked into price
    rewards_rate_of_retail: Decimal = D("0.00")  # fraction of retail reserved for rewards pool

    # Optional: “points issuance” operational cost (non-custodial, email->wallet mapping, etc.)
    points_ops_cost_per_order: Decimal = D("0.00")

    # Optional: “minting / settlement” cost (do not surface as crypto; internal only)
    settlement_cost_per_order: Decimal = D("0.00")

    # Optional: merchant-defined overhead reserve
    overhead_rate_of_retail: Decimal = D("0.00")

    # Optional: merchant-defined “risk buffer” (chargebacks, returns)
    risk_buffer_rate_of_retail: Decimal = D("0.00")


@dataclass(frozen=True)
class CostBreakdown:
    """
    A complete breakdown of revenue, costs, and net profit.

    All totals are per-unit, unless quantity > 1 in which case per-unit allocations apply for per-order fixed costs.
    """

    # Revenue
    retail_price: Decimal
    gross_revenue: Decimal

    # Costs
    cogs: Decimal
    payment_processor_fee: Decimal
    platform_fee: Decimal
    shipping: Decimal
    taxes: Decimal
    rewards_reserve: Decimal
    overhead_reserve: Decimal
    risk_buffer: Decimal
    points_ops: Decimal
    settlement: Decimal

    # Rollups
    total_costs: Decimal
    net_profit: Decimal
    net_margin: Decimal  # net_profit / gross_revenue (0..1)

    # Helpful meta
    quantity: int

    def to_dict(self) -> Dict[str, str]:
        """Serialize as strings to avoid float issues in JSON layers."""
        d = asdict(self)
        out: Dict[str, str] = {}
        for k, v in d.items():
            if isinstance(v, Decimal):
                out[k] = str(_q2(v))
            else:
                out[k] = str(v)
        return out


class CostModel:
    """
    Main entrypoint.

    Usage:
        breakdown = CostModel().compute(CostInputs(...))
    """

    def compute(self, inputs: CostInputs) -> CostBreakdown:
        if inputs.quantity < 1:
            raise ValueError("quantity must be >= 1")

        retail_price = D(inputs.retail_price)
        unit_cost = D(inputs.unit_cost)
        qty = int(inputs.quantity)

        # Revenue (per-unit)
        gross_revenue = retail_price

        # Allocate per-order fixed fees to per-unit
        per_unit_processor_fixed = D(inputs.payment_processor_fixed) / D(qty)
        per_unit_shipping = D(inputs.shipping_cost_per_order) / D(qty)
        per_unit_points_ops = D(inputs.points_ops_cost_per_order) / D(qty)
        per_unit_settlement = D(inputs.settlement_cost_per_order) / D(qty)

        # Taxes (simple model): tax on retail
        taxes = gross_revenue * D(inputs.tax_rate)

        # Processor: rate + fixed (rate applies to retail; adjust if your system taxes differently)
        processor_fee = (gross_revenue * D(inputs.payment_processor_rate)) + per_unit_processor_fixed

        # Platform fee: % of retail
        platform_fee = gross_revenue * D(inputs.platform_fee_rate)

        # Rewards reserve: baked in
        rewards_reserve = gross_revenue * D(inputs.rewards_rate_of_retail)

        # Optional reserves
        overhead_reserve = gross_revenue * D(inputs.overhead_rate_of_retail)
        risk_buffer = gross_revenue * D(inputs.risk_buffer_rate_of_retail)

        # COGS per unit
        cogs = unit_cost

        total_costs = (
            cogs
            + processor_fee
            + platform_fee
            + per_unit_shipping
            + taxes
            + rewards_reserve
            + overhead_reserve
            + risk_buffer
            + per_unit_points_ops
            + per_unit_settlement
        )

        net_profit = gross_revenue - total_costs
        net_margin = D("0.00")
        if gross_revenue > D("0.00"):
            net_margin = net_profit / gross_revenue

        return CostBreakdown(
            retail_price=_q2(retail_price),
            gross_revenue=_q2(gross_revenue),
            cogs=_q2(cogs),
            payment_processor_fee=_q2(processor_fee),
            platform_fee=_q2(platform_fee),
            shipping=_q2(per_unit_shipping),
            taxes=_q2(taxes),
            rewards_reserve=_q2(rewards_reserve),
            overhead_reserve=_q2(overhead_reserve),
            risk_buffer=_q2(risk_buffer),
            points_ops=_q2(per_unit_points_ops),
            settlement=_q2(per_unit_settlement),
            total_costs=_q2(total_costs),
            net_profit=_q2(net_profit),
            net_margin=_q4(net_margin),
            quantity=qty,
        )

    def explain(self, inputs: CostInputs) -> Dict[str, str]:
        """
        Human-readable, stable key output for logs/admin UIs.
        """
        b = self.compute(inputs)
        return {
            "retail_price": str(b.retail_price),
            "total_costs": str(b.total_costs),
            "net_profit": str(b.net_profit),
            "net_margin": str(b.net_margin),
        }
