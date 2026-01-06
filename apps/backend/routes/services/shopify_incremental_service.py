from typing import Any, Dict, Optional, Tuple

from apps.backend.lib.supabase_admin import (
    upsert_one,
    insert_one,
    rpc,
    select_many,
)

DEFAULT_TIERS = [
    {"name": "Tier 1", "min_spend": 0},
    {"name": "Tier 2", "min_spend": 500},
    {"name": "Tier 3", "min_spend": 2000},
]

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def _extract_email(order: Dict[str, Any]) -> Optional[str]:
    # Prefer order email; fallback to customer email if present
    email = order.get("email")
    if email:
        return str(email).strip().lower()
    cust = order.get("customer") or {}
    cemail = cust.get("email")
    return str(cemail).strip().lower() if cemail else None

def _pick_tier(lifetime_spend: float, tiers: list) -> str:
    chosen = tiers[0]["name"]
    for t in tiers:
        if lifetime_spend >= float(t.get("min_spend", 0)):
            chosen = t["name"]
    return chosen

def load_merchant_tiers(merchant_id: str) -> list:
    """
    Loads merchant-defined tiers if present; otherwise uses DEFAULT_TIERS.
    Expects a table `merchant_tiers` with columns: merchant_id, name, min_spend.
    """
    try:
        rows = select_many(
            "merchant_tiers",
            filters={"merchant_id": merchant_id},
            columns="name,min_spend",
            order="min_spend.asc"
        )
        if rows:
            return rows
    except Exception:
        # If table doesn't exist yet, we fall back safely.
        pass
    return DEFAULT_TIERS

def process_order_paid(
    *,
    merchant_id: str,
    points_per_dollar: float,
    order: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Idempotent incremental earn pipeline:
    - Upsert loyalty customer by email
    - Insert wallet_ledger(shopify_order, source_ref=order_id) (unique-index safe)
    - Atomically increment wallet_balances via RPC
    - Recompute tier based on lifetime_spend (best-effort)
    """
    order_id = str(order.get("id", "")).strip()
    if not order_id:
        return {"ok": False, "reason": "missing_order_id"}

    email = _extract_email(order)
    if not email:
        return {"ok": False, "reason": "missing_email"}

    total_price = _safe_float(order.get("total_price", 0))
    points = int(total_price * float(points_per_dollar or 1.0))

    # 1) Upsert customer
    customer = upsert_one(
        "loyalty_customers",
        {"merchant_id": merchant_id, "email": email},
        conflict_cols="merchant_id,email",
    )

    # 2) Insert ledger (idempotent via unique index)
    ledger_inserted = True
    try:
        insert_one(
            "wallet_ledger",
            {
                "merchant_id": merchant_id,
                "customer_id": customer["id"],
                "amount": points,
                "direction": "earn",
                "source": "shopify_order",
                "source_ref": order_id,
            },
        )
    except Exception:
        # Unique violation or already processed
        ledger_inserted = False

    # If the ledger wasn't inserted, do NOT increment balances again.
    if not ledger_inserted:
        return {
            "ok": True,
            "idempotent_skip": True,
            "merchant_id": merchant_id,
            "customer_id": customer["id"],
            "order_id": order_id,
        }

    # 3) Atomic balance increment
    bal_rows = rpc("increment_wallet_balance", {
        "p_merchant_id": merchant_id,
        "p_customer_id": customer["id"],
        "p_delta": points,
    })
    balance = bal_rows[0]["balance"] if bal_rows else None

    # 4) Tier recompute (best-effort, based on lifetime spend)
    lifetime_spend = total_price
    try:
        # If you have a customer profile table with lifetime spend, update it.
        # Otherwise we compute tier using just this order (safe fallback).
        tiers = load_merchant_tiers(merchant_id)
        tier_name = _pick_tier(lifetime_spend, tiers)
        # Store tier on a customer profile table if it exists; else do nothing.
        try:
            upsert_one(
                "loyalty_customer_profiles",
                {
                    "merchant_id": merchant_id,
                    "customer_id": customer["id"],
                    "tier": tier_name,
                },
                conflict_cols="merchant_id,customer_id",
            )
        except Exception:
            # If profiles table doesn't exist yet, skip without breaking engine.
            tier_name = tier_name
    except Exception:
        tier_name = None

    return {
        "ok": True,
        "merchant_id": merchant_id,
        "customer_id": customer["id"],
        "order_id": order_id,
        "points": points,
        "balance": balance,
        "tier": tier_name,
    }
