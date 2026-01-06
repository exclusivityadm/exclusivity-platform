from typing import Any, Dict, Optional

from apps.backend.routes.services.supabase_admin import (
    insert_one,
    upsert_one,
    rpc,
)

def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0

def _extract_email(order: Dict[str, Any]) -> Optional[str]:
    if order.get("email"):
        return order["email"].strip().lower()
    if order.get("customer") and order["customer"].get("email"):
        return order["customer"]["email"].strip().lower()
    return None

def process_order_paid(
    *,
    merchant_id: str,
    points_per_dollar: float,
    order: Dict[str, Any],
) -> Dict[str, Any]:

    order_id = str(order.get("id") or "")
    if not order_id:
        return {"ok": False, "reason": "missing_order_id"}

    email = _extract_email(order)
    if not email:
        return {"ok": False, "reason": "missing_email"}

    total_price = _safe_float(order.get("total_price"))
    points = int(total_price * points_per_dollar)

    customer = upsert_one(
        "loyalty_customers",
        {"merchant_id": merchant_id, "email": email},
        conflict_cols="merchant_id,email",
    )

    inserted = True
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
        inserted = False

    if not inserted:
        return {
            "ok": True,
            "idempotent": True,
            "merchant_id": merchant_id,
            "customer_id": customer["id"],
            "order_id": order_id,
        }

    bal = rpc(
        "increment_wallet_balance",
        {
            "p_merchant_id": merchant_id,
            "p_customer_id": customer["id"],
            "p_delta": points,
        },
    )

    return {
        "ok": True,
        "merchant_id": merchant_id,
        "customer_id": customer["id"],
        "order_id": order_id,
        "points": points,
        "balance": bal[0]["balance"] if bal else None,
    }
