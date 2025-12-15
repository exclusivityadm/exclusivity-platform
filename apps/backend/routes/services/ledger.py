# apps/backend/services/points.py
from typing import Optional, Dict, Any
from fastapi import HTTPException
from apps.backend.db import get_supabase

def award_points(merchant_id: str, customer_id: str, delta: int, reason: str = "", metadata: Optional[Dict[str, Any]] = None):
    """
    Minimal internal helper to write to ledger and balances.
    Safe to call from webhooks or routes.
    """
    sb = get_supabase()
    if not sb:
        raise HTTPException(501, "Supabase not configured")

    metadata = metadata or {}

    # Ensure customer exists (idempotent)
    exists = sb.table("customers").select("*") \
        .eq("merchant_id", merchant_id).eq("customer_id", customer_id) \
        .limit(1).execute()
    if not exists.data:
        sb.table("customers").insert({
            "merchant_id": merchant_id,
            "customer_id": customer_id
        }).execute()

    # Ledger write
    sb.table("points_ledger").insert({
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "delta": delta,
        "reason": reason,
        "metadata": metadata
    }).execute()

    # Balance upsert
    bal = sb.table("points_balances").select("*") \
        .eq("merchant_id", merchant_id).eq("customer_id", customer_id) \
        .limit(1).execute()
    current = bal.data[0]["points"] if bal.data else 0
    new_pts = int(current) + int(delta)

    if bal.data:
        sb.table("points_balances").update({
            "points": new_pts,
            "updated_at": "now()"
        }).eq("merchant_id", merchant_id).eq("customer_id", customer_id).execute()
    else:
        sb.table("points_balances").insert({
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "points": new_pts
        }).execute()

    return {"points": new_pts}
