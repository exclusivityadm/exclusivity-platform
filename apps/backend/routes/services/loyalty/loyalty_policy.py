"""
Loyalty Policy (Canonical)
==========================

Single source of truth for the loyalty program rules across the entire system.

Key requirements implemented:
- Tier progression is based ONLY on lifetime purchase amounts (lifetime spend).
- Rewards are baked into pricing; points issuance is deterministic.
- Program can be "silent" by default (not public-facing unless merchant chooses).
- Non-punitive: no forced downgrades, no scolding language, no coercive mechanics.

Non-goals:
- No DB access (pure domain rules).
- No HTTP / FastAPI logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR
from typing import Any, Dict, List, Optional, Literal


D = Decimal

DisclosureMode = Literal["silent", "disclosed"]
RoundingMode = Literal["nearest", "down"]


def _q2(x: Decimal) -> Decimal:
    return x.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def _q4(x: Decimal) -> Decimal:
    return x.quantize(D("0.0001"), rounding=ROUND_HALF_UP)


def _to_decimal(v: Any, default: Decimal = D("0")) -> Decimal:
    if v is None:
        return default
    if isinstance(v, Decimal):
        return v
    try:
        return D(str(v))
    except Exception:
        return default


@dataclass(frozen=True)
class Tier:
    """
    A tier is defined by a minimum lifetime spend threshold.

    Example:
        Bronze: min_lifetime_spend = 0
        Silver: min_lifetime_spend = 500
        Gold:   min_lifetime_spend = 2000
    """
    key: str
    name: str
    min_lifetime_spend: Decimal

    # Optional perks metadata (no business logic attached here)
    perks: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "min_lifetime_spend": str(_q2(self.min_lifetime_spend)),
            "perks": self.perks,
        }


@dataclass(frozen=True)
class PointsRule:
    """
    Canonical points valuation rules.

    points_per_currency_unit:
        - If 1 point = $0.01, then points_per_currency_unit = 100
          (because $1.00 earns 100 points *if fully eligible*).

    earn_rate_of_eligible_spend:
        - Fraction of eligible spend that becomes rewards value.
        - This should generally match your "rewards baked into price" reserve rate.
        - Example: if 2% of retail is reserved for rewards, earn_rate_of_eligible_spend = 0.02
    """
    points_label: str = "points"
    badges_label: str = "badges"

    # Points valuation
    points_per_currency_unit: Decimal = D("100")  # 100 points per $1.00 (=> 1 point = $0.01)

    # Earn math
    earn_rate_of_eligible_spend: Decimal = D("0.02")  # 2% of eligible spend becomes rewards value
    rounding: RoundingMode = "nearest"  # how to round points

    # Optional expiry in days (None => no expiry)
    points_expiry_days: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "points_label": self.points_label,
            "badges_label": self.badges_label,
            "points_per_currency_unit": str(_q4(self.points_per_currency_unit)),
            "earn_rate_of_eligible_spend": str(_q4(self.earn_rate_of_eligible_spend)),
            "rounding": self.rounding,
            "points_expiry_days": self.points_expiry_days,
        }


@dataclass(frozen=True)
class DisclosurePolicy:
    """
    Controls whether the program is visible to end customers by default.
    """
    mode: DisclosureMode = "silent"
    customer_facing_copy_hint: str = (
        "This program is typically silent by default. If disclosed, use plain language "
        "like points, badges, tiers — avoid technical implementation details."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "customer_facing_copy_hint": self.customer_facing_copy_hint,
        }


@dataclass(frozen=True)
class LoyaltyPolicy:
    """
    Top-level policy object for a merchant program.

    This object must be the single canonical configuration:
    - Pricing engine should align rewards reserve with PointsRule earn_rate_of_eligible_spend.
    - Tier engine should use tiers here, not duplicated elsewhere.
    """
    program_name: str = "Exclusivity"
    currency: str = "USD"

    tiers: List[Tier] = field(default_factory=list)
    points_rule: PointsRule = field(default_factory=PointsRule)
    disclosure: DisclosurePolicy = field(default_factory=DisclosurePolicy)

    # Non-punitive constraints
    allow_downgrades: bool = False  # lifetime-spend programs generally should not downgrade
    allow_negative_points_balance: bool = False  # typically prevent going below zero after adjustments

    # Audit / explanation settings
    version: str = "2025-12-14-canonical"
    notes: str = "Canonical loyalty policy. Tiering by lifetime spend only. Rewards baked into pricing."

    def __post_init__(self) -> None:
        # Ensure tiers exist and are valid
        if not self.tiers:
            object.__setattr__(self, "tiers", self.default_tiers())

        self._validate()

    # -----------------------------
    # Defaults
    # -----------------------------
    @staticmethod
    def default_tiers() -> List[Tier]:
        return [
            Tier(key="bronze", name="Bronze", min_lifetime_spend=D("0.00")),
            Tier(key="silver", name="Silver", min_lifetime_spend=D("500.00")),
            Tier(key="gold", name="Gold", min_lifetime_spend=D("2000.00")),
            Tier(key="platinum", name="Platinum", min_lifetime_spend=D("7500.00")),
            Tier(key="black_label", name="Black Label", min_lifetime_spend=D("25000.00")),
        ]

    # -----------------------------
    # Validation
    # -----------------------------
    def _validate(self) -> None:
        # Program basics
        if not self.program_name.strip():
            raise ValueError("program_name cannot be empty")
        if not self.currency.strip():
            raise ValueError("currency cannot be empty")

        # Points rule sanity
        pr = self.points_rule
        if pr.points_per_currency_unit <= D("0"):
            raise ValueError("points_per_currency_unit must be > 0")
        if pr.earn_rate_of_eligible_spend < D("0") or pr.earn_rate_of_eligible_spend >= D("1"):
            raise ValueError("earn_rate_of_eligible_spend must be between 0 and < 1")
        if pr.rounding not in ("nearest", "down"):
            raise ValueError("points rounding must be 'nearest' or 'down'")
        if pr.points_expiry_days is not None and pr.points_expiry_days <= 0:
            raise ValueError("points_expiry_days must be > 0 if set")

        # Tiers sanity
        if len(self.tiers) < 1:
            raise ValueError("tiers must contain at least one tier")

        # Keys must be unique and thresholds non-decreasing
        seen = set()
        sorted_tiers = sorted(self.tiers, key=lambda t: t.min_lifetime_spend)
        for t in sorted_tiers:
            if not t.key.strip():
                raise ValueError("tier.key cannot be empty")
            if t.key in seen:
                raise ValueError(f"duplicate tier key: {t.key}")
            seen.add(t.key)
            if t.min_lifetime_spend < D("0"):
                raise ValueError("tier.min_lifetime_spend cannot be negative")

        # Ensure first tier starts at 0 to avoid undefined state
        if sorted_tiers[0].min_lifetime_spend != D("0.00"):
            raise ValueError("first tier must have min_lifetime_spend = 0.00")

    # -----------------------------
    # Tier logic
    # -----------------------------
    def tier_for_lifetime_spend(self, lifetime_spend: Decimal) -> Tier:
        """
        Returns the tier matching a lifetime spend total.
        Deterministic, based ONLY on lifetime spend.
        """
        spend = _to_decimal(lifetime_spend, D("0.00"))
        if spend < D("0.00"):
            spend = D("0.00")

        sorted_tiers = sorted(self.tiers, key=lambda t: t.min_lifetime_spend)
        current = sorted_tiers[0]
        for t in sorted_tiers:
            if spend >= t.min_lifetime_spend:
                current = t
            else:
                break
        return current

    def next_tier(self, lifetime_spend: Decimal) -> Optional[Tier]:
        """
        Returns the next tier above the current tier, if any.
        """
        spend = _to_decimal(lifetime_spend, D("0.00"))
        if spend < D("0.00"):
            spend = D("0.00")

        sorted_tiers = sorted(self.tiers, key=lambda t: t.min_lifetime_spend)
        current = self.tier_for_lifetime_spend(spend)
        for t in sorted_tiers:
            if t.min_lifetime_spend > current.min_lifetime_spend:
                return t
        return None

    def amount_to_next_tier(self, lifetime_spend: Decimal) -> Optional[Decimal]:
        """
        How much additional lifetime spend is needed to reach the next tier.
        Returns None if already at top tier.
        """
        spend = _to_decimal(lifetime_spend, D("0.00"))
        if spend < D("0.00"):
            spend = D("0.00")

        nt = self.next_tier(spend)
        if nt is None:
            return None
        remaining = nt.min_lifetime_spend - spend
        if remaining < D("0.00"):
            remaining = D("0.00")
        return _q2(remaining)

    # -----------------------------
    # Points logic
    # -----------------------------
    def points_for_eligible_spend(self, eligible_spend: Decimal) -> int:
        """
        Convert eligible spend (currency) into points earned.

        Earn math:
            rewards_value = eligible_spend * earn_rate_of_eligible_spend
            points = rewards_value * points_per_currency_unit

        Rounding:
            - nearest: round half up
            - down: floor
        """
        spend = _to_decimal(eligible_spend, D("0.00"))
        if spend <= D("0.00"):
            return 0

        pr = self.points_rule
        rewards_value = spend * pr.earn_rate_of_eligible_spend
        raw_points = rewards_value * pr.points_per_currency_unit

        if pr.rounding == "down":
            pts = int(raw_points.to_integral_value(rounding=ROUND_FLOOR))
        else:
            pts = int(raw_points.to_integral_value(rounding=ROUND_HALF_UP))

        if pts < 0:
            pts = 0
        return pts

    def currency_value_for_points(self, points: int) -> Decimal:
        """
        Convert points back into currency value using valuation:
            currency = points / points_per_currency_unit
        """
        pr = self.points_rule
        pts = max(0, int(points))
        value = D(pts) / pr.points_per_currency_unit
        return _q2(value)

    # -----------------------------
    # Disclosure / language helpers
    # -----------------------------
    def customer_visibility_mode(self) -> DisclosureMode:
        return self.disclosure.mode

    def preferred_labels(self) -> Dict[str, str]:
        return {
            "points_label": self.points_rule.points_label,
            "badges_label": self.points_rule.badges_label,
        }

    # -----------------------------
    # Serialization
    # -----------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "program_name": self.program_name,
            "currency": self.currency,
            "tiers": [t.to_dict() for t in sorted(self.tiers, key=lambda t: t.min_lifetime_spend)],
            "points_rule": self.points_rule.to_dict(),
            "disclosure": self.disclosure.to_dict(),
            "allow_downgrades": self.allow_downgrades,
            "allow_negative_points_balance": self.allow_negative_points_balance,
            "version": self.version,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "LoyaltyPolicy":
        """
        Create a LoyaltyPolicy from a dict (e.g., DB-stored JSON).
        Missing fields will fall back to canonical defaults.
        """
        data = data or {}

        tiers_in = data.get("tiers") or []
        tiers: List[Tier] = []
        for t in tiers_in:
            if not isinstance(t, dict):
                continue
            tiers.append(
                Tier(
                    key=str(t.get("key", "")).strip(),
                    name=str(t.get("name", "")).strip() or str(t.get("key", "")).strip().title(),
                    min_lifetime_spend=_to_decimal(t.get("min_lifetime_spend"), D("0.00")),
                    perks=t.get("perks") if isinstance(t.get("perks"), dict) else {},
                )
            )

        pr_in = data.get("points_rule") if isinstance(data.get("points_rule"), dict) else {}
        points_rule = PointsRule(
            points_label=str(pr_in.get("points_label", "points")),
            badges_label=str(pr_in.get("badges_label", "badges")),
            points_per_currency_unit=_to_decimal(pr_in.get("points_per_currency_unit"), D("100")),
            earn_rate_of_eligible_spend=_to_decimal(pr_in.get("earn_rate_of_eligible_spend"), D("0.02")),
            rounding=str(pr_in.get("rounding", "nearest")),  # validated in __post_init__
            points_expiry_days=pr_in.get("points_expiry_days", None),
        )

        disc_in = data.get("disclosure") if isinstance(data.get("disclosure"), dict) else {}
        disclosure = DisclosurePolicy(
            mode=str(disc_in.get("mode", "silent")),  # validated indirectly by Literal usage expectations
            customer_facing_copy_hint=str(
                disc_in.get(
                    "customer_facing_copy_hint",
                    DisclosurePolicy().customer_facing_copy_hint,
                )
            ),
        )

        return LoyaltyPolicy(
            program_name=str(data.get("program_name", "Exclusivity")),
            currency=str(data.get("currency", "USD")),
            tiers=tiers if tiers else LoyaltyPolicy.default_tiers(),
            points_rule=points_rule,
            disclosure=disclosure,
            allow_downgrades=bool(data.get("allow_downgrades", False)),
            allow_negative_points_balance=bool(data.get("allow_negative_points_balance", False)),
            version=str(data.get("version", "2025-12-14-canonical")),
            notes=str(data.get("notes", LoyaltyPolicy().notes)),
        )

    # -----------------------------
    # Canonical explanation helpers (AI/admin)
    # -----------------------------
    def explain_tier_status(self, lifetime_spend: Decimal) -> Dict[str, Any]:
        """
        Plain-language, stable explanation payload for AI/admin UIs.
        """
        spend = _to_decimal(lifetime_spend, D("0.00"))
        spend = max(D("0.00"), spend)

        current = self.tier_for_lifetime_spend(spend)
        nxt = self.next_tier(spend)
        remaining = self.amount_to_next_tier(spend)

        return {
            "current_tier": {"key": current.key, "name": current.name},
            "lifetime_spend": str(_q2(spend)),
            "next_tier": None if nxt is None else {"key": nxt.key, "name": nxt.name},
            "amount_to_next_tier": None if remaining is None else str(_q2(remaining)),
            "rule": "Tier progression is based only on lifetime spend.",
            "non_punitive": True,
        }
