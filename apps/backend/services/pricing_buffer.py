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
    sb = get_supabase()
    if not sb:
        return {"ok": False, "error": "Supabase not configured"}

    snap = (
        sb.table("merchant_catalog_snapshots")
        .select("*")
        .eq("merchant_id", merchant_id)
        .order("captured_at", desc=True)
        .limit(1)
        .execute()
    )

    products: List[Dict[str, Any]] = []
    shop_domain: Optional[str] = None
    snapshot_error: Optional[str] = None

    if snap.data:
        row = snap.data[0]
        shop_domain = row.get("shop_domain")
        payload = row.get("payload") or {}
        products = payload.get("products") or []
        snapshot_error = payload.get("error")

    buffer_cents = _int_env("EXCL_FLAT_BUFFER_CENTS", 75)  # $0.75 per item default

    recommendations = []
    for p in products:
        title = p.get("title")
        for v in (p.get("variants") or []):
            recommendations.append({
                "product_title": title,
                "variant_id": str(v.get("id")) if v.get("id") is not None else None,
                "sku": v.get("sku"),
                "current_price": v.get("price"),
                "suggested_additional_cents": buffer_cents,
                "explanation": "Adds a small operational buffer per item to cover loyalty + infrastructure costs invisibly.",
            })

    sb.table("merchant_pricing_recommendations").insert({
        "merchant_id": merchant_id,
        "shop_domain": shop_domain or "",
        "strategy": "flat_buffer",
        "buffer_cents": buffer_cents,
        "notes": "v1 flat buffer. Present as pricing optimization (no crypto language).",
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
