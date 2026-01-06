from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from apps.backend.routes.services.supabase_admin import (
    insert_one,
    upsert_one,
    select_one,
    select_many,
)

def _to_cents(value: Any) -> int:
    """
    Accepts dollars (float/str) or cents (int) if provided by caller.
    If it looks like a float, treat as dollars.
    """
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    try:
        s = str(value).strip()
        # If contains '.', treat as dollars
        if "." in s:
            return int(round(float(s) * 100))
        # Otherwise treat as cents if caller passed cents as string
        return int(s)
    except Exception:
        return 0

def _clamp_int(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

def get_or_create_pricing_policy(merchant_id: str) -> Dict[str, Any]:
    policy = select_one("merchant_pricing_policy", {"merchant_id": merchant_id})
    if policy:
        return policy
    # Create default policy
    return insert_one("merchant_pricing_policy", {
        "merchant_id": merchant_id,
        "points_per_dollar": 1.0,
        "recommended_uplift_percent": 3.0,
        "min_buffer_cents": 50,
        "est_mint_cost_cents": 25,
    })

def create_catalog_snapshot(
    *,
    merchant_id: str,
    source: str,
    notes: Optional[str],
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Creates a snapshot + item rows. Prices stored in cents.
    """
    snap = insert_one("pricing_catalog_snapshots", {
        "merchant_id": merchant_id,
        "source": source or "manual",
        "item_count": len(items),
        "notes": notes,
    })

    # Insert items one-by-one (simple + reliable for now)
    for it in items:
        insert_one("pricing_catalog_items", {
            "snapshot_id": snap["id"],
            "merchant_id": merchant_id,
            "product_ref": it.get("product_ref"),
            "variant_ref": it.get("variant_ref"),
            "sku": it.get("sku"),
            "title": it.get("title"),
            "currency": (it.get("currency") or "USD"),
            "base_price_cents": _to_cents(it.get("base_price")),
            "compare_at_cents": _to_cents(it.get("compare_at")) if it.get("compare_at") is not None else None,
            "cost_cents": _to_cents(it.get("cost")) if it.get("cost") is not None else None,
            "taxable": bool(it.get("taxable", True)),
            "active": bool(it.get("active", True)),
        })

    return snap

def _compute_recommended_price(
    *,
    base_cents: int,
    uplift_percent: float,
    buffer_cents: int,
) -> Tuple[int, int]:
    uplift = int(round(base_cents * (uplift_percent / 100.0)))
    recommended = base_cents + uplift + buffer_cents
    delta = recommended - base_cents
    return recommended, delta

def generate_recommendations(
    *,
    merchant_id: str,
    snapshot_id: str,
    uplift_percent: Optional[float] = None,
    buffer_cents: Optional[int] = None,
    est_mint_cost_cents: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Builds a recommendation set for all active items in the snapshot.
    Strategy: uplift + buffer (gas baked-in abstraction)
    """
    policy = get_or_create_pricing_policy(merchant_id)

    u = _safe_float(uplift_percent, _safe_float(policy.get("recommended_uplift_percent"), 3.0))
    # guardrails: 0%..25%
    u = max(0.0, min(25.0, u))

    b = buffer_cents if buffer_cents is not None else int(policy.get("min_buffer_cents") or 50)
    b = _clamp_int(int(b), 0, 5000)

    est = est_mint_cost_cents if est_mint_cost_cents is not None else int(policy.get("est_mint_cost_cents") or 25)
    est = _clamp_int(int(est), 0, 5000)

    # Pull snapshot items
    items = select_many(
        "pricing_catalog_items",
        filters={"snapshot_id": snapshot_id},
        columns="product_ref,variant_ref,sku,title,currency,base_price_cents,active",
        order="created_at.asc",
        limit=None,
    )

    reco = insert_one("pricing_recommendations", {
        "merchant_id": merchant_id,
        "snapshot_id": snapshot_id,
        "strategy": "uplift_plus_buffer",
        "uplift_percent": u,
        "buffer_cents": b,
        "est_mint_cost_cents": est,
    })

    created = 0
    for it in items:
        if it.get("active") is False:
            continue
        base = int(it.get("base_price_cents") or 0)
        rec_price, delta = _compute_recommended_price(
            base_cents=base,
            uplift_percent=u,
            buffer_cents=b,
        )
        rationale = f"Base + {u:.2f}% uplift + {b}¢ buffer (est mint {est}¢)"
        insert_one("pricing_recommendation_items", {
            "recommendation_id": reco["id"],
            "merchant_id": merchant_id,
            "product_ref": it.get("product_ref"),
            "variant_ref": it.get("variant_ref"),
            "sku": it.get("sku"),
            "title": it.get("title"),
            "currency": it.get("currency") or "USD",
            "base_price_cents": base,
            "recommended_price_cents": rec_price,
            "delta_cents": delta,
            "rationale": rationale,
        })
        created += 1

    return {
        "recommendation_id": reco["id"],
        "merchant_id": merchant_id,
        "snapshot_id": snapshot_id,
        "strategy": reco["strategy"],
        "uplift_percent": float(reco["uplift_percent"]),
        "buffer_cents": int(reco["buffer_cents"]),
        "est_mint_cost_cents": int(reco["est_mint_cost_cents"]),
        "items_created": created,
    }

def latest_recommendation_for_merchant(merchant_id: str) -> Optional[Dict[str, Any]]:
    recos = select_many(
        "pricing_recommendations",
        filters={"merchant_id": merchant_id},
        columns="id,merchant_id,snapshot_id,strategy,uplift_percent,buffer_cents,est_mint_cost_cents,created_at",
        order="created_at.desc",
        limit=1,
    )
    return recos[0] if recos else None

def recommendation_items(recommendation_id: str) -> List[Dict[str, Any]]:
    return select_many(
        "pricing_recommendation_items",
        filters={"recommendation_id": recommendation_id},
        columns="product_ref,variant_ref,sku,title,currency,base_price_cents,recommended_price_cents,delta_cents,rationale",
        order="created_at.asc",
        limit=None,
    )
