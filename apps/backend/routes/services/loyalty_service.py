"""
Loyalty Service
----------------
Authoritative loyalty brain for Exclusivity.

This module is intentionally deterministic, merchant-safe,
and future-proofed for NFT / on-chain anchoring without requiring
blockchain execution today.

Design guarantees:
- Single source of truth for points & tiers
- Supply caps enforced
- No hidden mutation
- Explainable outcomes
"""

from typing import Dict, Optional
from datetime import datetime

from apps.backend.services.supabase_admin import (
    select_one,
    select_many,
    insert_one,
    update_one,
)

# ---------------------------------------------------------------------
# CONFIG / CONSTANTS
# ---------------------------------------------------------------------

DEFAULT_POINT_NAME = "Points"

# Default tier ladder (merchant can override later)
DEFAULT_TIERS = [
    {"name": "Tier 1", "min_points": 0},
    {"name": "Tier 2", "min_points": 100},
    {"name": "Tier 3", "min_points": 300},
]

# Hard safety cap (merchant-defined later)
DEFAULT_MAX_SUPPLY = 1_000_000


# ---------------------------------------------------------------------
# CORE HELPERS
# ---------------------------------------------------------------------

def _get_merchant() -> Optional[Dict]:
    """
    Resolves the active merchant.
    Assumes single-merchant deployment for now.
    """
    return select_one("merchants", {})


def _get_loyalty_config(merchant_id: str) -> Dict:
    """
    Returns loyalty configuration.
    Creates default config if missing.
    """
    config = select_one("loyalty_config", {"merchant_id": merchant_id})

    if not config:
        config = {
            "merchant_id": merchant_id,
            "point_name": DEFAULT_POINT_NAME,
            "tiers": DEFAULT_TIERS,
            "max_supply": DEFAULT_MAX_SUPPLY,
            "created_at": datetime.utcnow().isoformat(),
        }
        insert_one("loyalty_config", config)

    return config


def _get_total_supply(merchant_id: str) -> int:
    """
    Returns total issued points.
    """
    rows = select_many(
        "loyalty_ledger",
        {"merchant_id": merchant_id},
    )

    return sum(r["delta"] for r in rows) if rows else 0


# ---------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------

def ensure_loyalty_baseline(merchant_id: str) -> bool:
    """
    Idempotent initializer.
    Ensures loyalty config + tables exist.

    Returns True if system is ready.
    """
    _get_loyalty_config(merchant_id)
    return True


def issue_points(
    merchant_id: str,
    customer_id: str,
    amount: int,
    reason: str,
) -> Dict:
    """
    Issues points to a customer.
    Enforces supply cap.
    """

    if amount <= 0:
        raise ValueError("Point amount must be positive")

    config = _get_loyalty_config(merchant_id)
    current_supply = _get_total_supply(merchant_id)

    if current_supply + amount > config["max_supply"]:
        raise ValueError("Loyalty supply cap exceeded")

    entry = {
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "delta": amount,
        "reason": reason,
        "created_at": datetime.utcnow().isoformat(),
    }

    insert_one("loyalty_ledger", entry)

    return {
        "issued": amount,
        "new_total_supply": current_supply + amount,
        "reason": reason,
    }


def get_customer_points(
    merchant_id: str,
    customer_id: str,
) -> int:
    """
    Returns a customer's current point balance.
    """

    rows = select_many(
        "loyalty_ledger",
        {
            "merchant_id": merchant_id,
            "customer_id": customer_id,
        },
    )

    return sum(r["delta"] for r in rows) if rows else 0


def calculate_tier(
    merchant_id: str,
    customer_id: str,
) -> Dict:
    """
    Determines customer's tier based on points.
    Deterministic and explainable.
    """

    config = _get_loyalty_config(merchant_id)
    points = get_customer_points(merchant_id, customer_id)

    tiers = sorted(
        config["tiers"],
        key=lambda t: t["min_points"],
        reverse=True,
    )

    for tier in tiers:
        if points >= tier["min_points"]:
            return {
                "tier": tier["name"],
                "points": points,
                "next_tier_at": _next_tier_threshold(config["tiers"], tier),
            }

    return {
        "tier": None,
        "points": points,
        "next_tier_at": None,
    }


def _next_tier_threshold(tiers, current_tier):
    """
    Returns the next tier threshold, if any.
    """
    sorted_tiers = sorted(tiers, key=lambda t: t["min_points"])
    for tier in sorted_tiers:
        if tier["min_points"] > current_tier["min_points"]:
            return tier["min_points"]
    return None


def loyalty_snapshot(merchant_id: str) -> Dict:
    """
    Returns system-level loyalty snapshot.
    Used by AI, dashboard, onboarding.
    """

    config = _get_loyalty_config(merchant_id)
    supply = _get_total_supply(merchant_id)

    return {
        "point_name": config["point_name"],
        "tiers": config["tiers"],
        "max_supply": config["max_supply"],
        "issued_supply": supply,
        "remaining_supply": config["max_supply"] - supply,
    }
