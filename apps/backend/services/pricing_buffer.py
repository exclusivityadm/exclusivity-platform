from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from apps.backend.db import get_supabase


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def generate_pricing_recommendations(merchant_id: str) -> Dict[str, Any]:
    """
    v1: Flat buffer recommendation.
    This implements your economic model safely:
    - AI will *explain* and *suggest* in Preview tier
    - Paid tiers can later auto-apply (separate feature gate)
    """
    sb = get_supabase()
    if not sb:
        return {"ok": False, "error": "Supabase not configured"}

    # Latest catalog snapshot (if any)
    snap = sb.table("merchant_catalog_snapshots")\
        .select("*")\
        .eq("merchant_id", merchant_id)\
        .order("captured_at", desc=True)\
        .limit(1)\
        .execute()

    products: List[Dict[str, Any]] = []
    shop_domain: Optional[str] = None
    snapshot_error: Optional[str] = None

    if snap.data:
        row = snap.data[0]
        shop_domain = row.get("shop_domain")
        payload = row.get("payload") or {}
        products = payload.get("products") or []
        snapshot_error = payload.get("error")

    # Flat buffer cents: intentionally "well above" expected settlement costs
    # You can tune this later; keep it high enough to cover variability.
    buffer_cents = _int_env("EXCL_FLAT_BUFFER_CENTS", 75)  # default $0.75 per item

    # Build per-variant suggestions (best-effort)
    recommendations = []
    for p in products:
        title = p.get("title")
        for v in (p.get("variants") or []):
            sku = v.get("sku")
            price = v.get("price")
            variant_id = v.get("id")
            recommendations.append({
                "product_title": title,
                "variant_id": str(variant_id) if variant_id is not None else None,
                "sku": sku,
                "current_price": price,
                "suggested_additional_cents": buffer_cents,
                "explanation": "Adds a small operational buffer per item to cover loyalty + infrastructure costs invisibly.",
            })

    # Store result
    shop_domain = shop_domain or ""
    sb.table("merchant_pricing_recommendations").insert({
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "captured_at": _utcnow(),
        "strategy": "flat_buffer",
        "buffer_cents": buffer_cents,
        "notes": "v1 flat buffer. AI will present this as pricing optimization (no crypto language).",
        "payload": {
            "snapshot_error": snapshot_error,
            "recommendations": recommendations,
        },
    }).execute()

    return {
        "ok": True,
        "merchant_id": merchant_id,
        "buffer_cents": buffer_cents,
        "recommendations_count": len(recommendations),
        "snapshot_error": snapshot_error,
    }
