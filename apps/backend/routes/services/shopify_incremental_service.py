from typing import Any, Dict, List, Optional

from apps.backend.routes.services.supabase_admin import (
    insert_one,
    upsert_one,
    select_many,
    rpc,
)

DEFAULT_TIERS = [
    {"name": "Tier 1", "min_spend": 0},
    {"name": "Tier 2", "min_spend": 500},
    {"name": "Tier 3", "min_spend": 2000},
]

def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0

def _extract_email(order: Dict[str, Any]) -> Optional[str]:
    if order.get("email"):
        return str(order["email"]).strip().lower()
    cust = order.get("customer") or {}
    if cust.get("email"):
        return str(cust["email"]).strip().lower()
    return None

def load_merchant_tiers(merchant_id: str) -> List[Dict[str, Any]]:
    try:
        rows = select_many(
            "merchant_tiers",
            filters={"merchant_id": merchant_id},
            columns="name,min_spend",
            order="min_spend.asc",
        )
        if rows:
            # Normalize
            out = []
            for r in rows:
                out.append({"name": r.get("name"), "min_spend": _safe_float(r.get("min_spend"))})
            return out
    except Exception:
        pass
    return DEFAULT_TIERS

def pick_tier(lifetime_spend: float, tiers: List[Dict[str, Any]]) -> str:
    tiers_sorted = sorted(tiers, key=lambda t: float(t.get("min_spend", 0)))
    chosen = tiers_sorted[0]["name"] if tiers_sorted else "Tier 1"
    for t in tiers_sorted:
        if lifetime_spend >= float(t.get("min_spend", 0)):
            chosen = t.get("name") or chosen
    return chosen

def idempotent_ledger_insert(row: Dict[str, Any]) -> bool:
    try:
        insert_one("wallet_ledger", row)
        return True
    except Exception:
        return False

def atomic_balance_delta(merchant_id: str, customer_id: str, delta_points: int) -> Optional[int]:
    rows = rpc("increment_wallet_balance", {
        "p_merchant_id": merchant_id,
        "p_customer_id": customer_id,
        "p_delta": int(delta_points),
    })
    return rows[0]["balance"] if rows else None

def atomic_profile_delta(merchant_id: str, customer_id: str, spend_delta: float, order_delta: int) -> Dict[str, Any]:
    rows = rpc("increment_customer_profile", {
        "p_merchant_id": merchant_id,
        "p_customer_id": customer_id,
        "p_spend_delta": float(spend_delta),
        "p_order_delta": int(order_delta),
    })
    return rows[0] if rows else {"lifetime_spend": 0, "order_count": 0}

def set_profile_tier(merchant_id: str, customer_id: str, tier: str) -> None:
    upsert_one(
        "loyalty_customer_profiles",
        {
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "tier": tier,
        },
        conflict_cols="merchant_id,customer_id",
    )

def process_order_paid(*, merchant_id: str, points_per_dollar: float, order: Dict[str, Any]) -> Dict[str, Any]:
    order_id = str(order.get("id") or "").strip()
    if not order_id:
        return {"ok": False, "reason": "missing_order_id"}

    email = _extract_email(order)
    if not email:
        return {"ok": False, "reason": "missing_email"}

    total_price = _safe_float(order.get("total_price"))
    points = int(total_price * float(points_per_dollar or 1.0))

    customer = upsert_one(
        "loyalty_customers",
        {"merchant_id": merchant_id, "email": email},
        conflict_cols="merchant_id,email",
    )

    inserted = idempotent_ledger_insert({
        "merchant_id": merchant_id,
        "customer_id": customer["id"],
        "amount": points,
        "direction": "earn",
        "source": "shopify_order",
        "source_ref": order_id,
    })

    if not inserted:
        return {"ok": True, "idempotent": True, "event": "orders/paid", "order_id": order_id}

    balance = atomic_balance_delta(merchant_id, customer["id"], points)
    profile = atomic_profile_delta(merchant_id, customer["id"], spend_delta=total_price, order_delta=1)

    tiers = load_merchant_tiers(merchant_id)
    tier = pick_tier(float(profile.get("lifetime_spend", 0)), tiers)
    set_profile_tier(merchant_id, customer["id"], tier)

    return {
        "ok": True,
        "event": "orders/paid",
        "order_id": order_id,
        "customer_id": customer["id"],
        "points": points,
        "balance": balance,
        "lifetime_spend": float(profile.get("lifetime_spend", 0)),
        "order_count": int(profile.get("order_count", 0)),
        "tier": tier,
    }

def _compute_refund_amount(order: Dict[str, Any]) -> float:
    refunds = order.get("refunds") or []
    amt = 0.0
    for rf in refunds:
        for tx in (rf.get("transactions") or []):
            if str(tx.get("kind") or "").lower() == "refund":
                amt += _safe_float(tx.get("amount"))
    if amt > 0:
        return amt
    return _safe_float(order.get("total_price"))

def process_order_refunded(*, merchant_id: str, points_per_dollar: float, order: Dict[str, Any]) -> Dict[str, Any]:
    order_id = str(order.get("id") or "").strip()
    if not order_id:
        return {"ok": False, "reason": "missing_order_id"}

    email = _extract_email(order)
    if not email:
        return {"ok": False, "reason": "missing_email"}

    refund_amount = _compute_refund_amount(order)
    points = int(refund_amount * float(points_per_dollar or 1.0))

    customer = upsert_one(
        "loyalty_customers",
        {"merchant_id": merchant_id, "email": email},
        conflict_cols="merchant_id,email",
    )

    refunds = order.get("refunds") or []
    refund_id = str(refunds[0]["id"]) if refunds and refunds[0].get("id") else None
    source_ref = refund_id or f"{order_id}:refunded"

    inserted = idempotent_ledger_insert({
        "merchant_id": merchant_id,
        "customer_id": customer["id"],
        "amount": points,
        "direction": "redeem",
        "source": "shopify_refund",
        "source_ref": source_ref,
    })

    if not inserted:
        return {"ok": True, "idempotent": True, "event": "orders/refunded", "order_id": order_id, "refund_ref": source_ref}

    balance = atomic_balance_delta(merchant_id, customer["id"], -points)
    profile = atomic_profile_delta(merchant_id, customer["id"], spend_delta=-refund_amount, order_delta=0)

    tiers = load_merchant_tiers(merchant_id)
    tier = pick_tier(float(profile.get("lifetime_spend", 0)), tiers)
    set_profile_tier(merchant_id, customer["id"], tier)

    return {
        "ok": True,
        "event": "orders/refunded",
        "order_id": order_id,
        "refund_ref": source_ref,
        "customer_id": customer["id"],
        "points_debited": points,
        "balance": balance,
        "lifetime_spend": float(profile.get("lifetime_spend", 0)),
        "order_count": int(profile.get("order_count", 0)),
        "tier": tier,
    }

def process_order_cancelled(*, merchant_id: str, points_per_dollar: float, order: Dict[str, Any]) -> Dict[str, Any]:
    """
    orders/cancelled:
    - Treat as a debit of previously earned points for that order (best-effort)
    - Uses unique source 'shopify_cancelled'
    """
    order_id = str(order.get("id") or "").strip()
    if not order_id:
        return {"ok": False, "reason": "missing_order_id"}

    email = _extract_email(order)
    if not email:
        return {"ok": False, "reason": "missing_email"}

    total_price = _safe_float(order.get("total_price"))
    points = int(total_price * float(points_per_dollar or 1.0))

    customer = upsert_one(
        "loyalty_customers",
        {"merchant_id": merchant_id, "email": email},
        conflict_cols="merchant_id,email",
    )

    source_ref = f"{order_id}:cancelled"

    inserted = idempotent_ledger_insert({
        "merchant_id": merchant_id,
        "customer_id": customer["id"],
        "amount": points,
        "direction": "redeem",
        "source": "shopify_cancelled",
        "source_ref": source_ref,
    })

    if not inserted:
        return {"ok": True, "idempotent": True, "event": "orders/cancelled", "order_id": order_id}

    balance = atomic_balance_delta(merchant_id, customer["id"], -points)

    # Cancelled generally indicates the sale should not count toward lifetime spend.
    profile = atomic_profile_delta(merchant_id, customer["id"], spend_delta=-total_price, order_delta=-1)

    tiers = load_merchant_tiers(merchant_id)
    tier = pick_tier(float(profile.get("lifetime_spend", 0)), tiers)
    set_profile_tier(merchant_id, customer["id"], tier)

    return {
        "ok": True,
        "event": "orders/cancelled",
        "order_id": order_id,
        "customer_id": customer["id"],
        "points_debited": points,
        "balance": balance,
        "lifetime_spend": float(profile.get("lifetime_spend", 0)),
        "order_count": int(profile.get("order_count", 0)),
        "tier": tier,
    }
