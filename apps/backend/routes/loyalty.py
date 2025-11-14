# =====================================================
# 🪙 Exclusivity Backend - Loyalty Routes (Merged)
# =====================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from typing import Optional, Dict, Any, List

# If your project uses this import path, keep it. Otherwise, adjust.
from supabase import create_client, Client

router = APIRouter()

# -----------------------------------------------------
# 🔧 Helper: Create Supabase client (PRESERVED)
# -----------------------------------------------------
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Missing Supabase credentials in environment.")
    return create_client(url, key)

# -----------------------------------------------------
# 🩺 Health & Database Connectivity Test (PRESERVED)
#    GET /loyalty/test-db  (or /test-db if included without prefix)
# -----------------------------------------------------
@router.get("/test-db", tags=["loyalty"])
def test_db_connection():
    """
    Confirms database connection and basic read access.
    Returns True + record count if successful.
    """
    try:
        client = get_supabase_client()
        response = client.table("profiles").select("*").limit(1).execute()
        record_count = len(response.data) if response.data else 0
        return {
            "connected": True,
            "records": record_count,
            "database_url": os.getenv("SUPABASE_URL"),
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}

# -----------------------------------------------------
# 📊 Placeholder Loyalty Endpoints (PRESERVED)
#    GET /loyalty/tiers
#    GET /loyalty/tokens
# -----------------------------------------------------
@router.get("/tiers", tags=["loyalty"])
def get_loyalty_tiers():
    """
    Placeholder endpoint for tier retrieval.
    If a real 'loyalty_tier' table exists, we will return its rows.
    Otherwise fall back to static placeholders.
    """
    try:
        client = get_supabase_client()
        rows = client.table("loyalty_tier").select("*").execute().data  # may raise if table missing
        # Normalize result
        tiers = [
            {"name": r.get("name"), "threshold": int(r.get("threshold_points", 0))}
            for r in (rows or [])
        ]
        if tiers:
            return {"tiers": tiers}
    except Exception:
        pass  # fall back to placeholders if table not found or any error

    # Fallback placeholders (original behavior)
    return {
        "tiers": [
            {"name": "Silver", "threshold": 0},
            {"name": "Gold", "threshold": 5000},
            {"name": "Platinum", "threshold": 15000},
        ]
    }

@router.get("/tokens", tags=["loyalty"])
def get_loyalty_tokens():
    """
    Placeholder endpoint for token balance retrieval.
    """
    return {
        "tokens": {
            "balance": 0,
            "symbol": "LUX",
            "chain": "Base Mainnet"
        }
    }

# -----------------------------------------------------
# 🧮 NEW: Points & Tier Resolution (additive)
#    POST /loyalty/accrue       -> add to points_ledger
#    GET  /loyalty/points/total -> total points (+ tier if available)
# -----------------------------------------------------

class AccrueIn(BaseModel):
    merchant_id: str
    customer_id: str
    points: int
    reason: str
    ref: Optional[Dict[str, Any]] = None

def _sum_points(client: Client, merchant_id: str, customer_id: str) -> int:
    """
    Try RPC sum_points(m uuid, c text) if it exists, otherwise sum in Python.
    """
    # Attempt RPC first (if you've created it)
    try:
        rpc = client.rpc("sum_points", {"m": merchant_id, "c": customer_id}).execute()
        if getattr(rpc, "data", None):
            # rpc.data could be a list or dict depending on driver; normalize both
            data = rpc.data
            if isinstance(data, list) and data:
                return int(data[0].get("sum") or 0)
            if isinstance(data, dict):
                return int(data.get("sum") or 0)
    except Exception:
        pass

    # Fallback: select deltas and sum here
    rows = client.table("points_ledger") \
        .select("delta") \
        .eq("merchant_id", merchant_id) \
        .eq("customer_id", customer_id) \
        .execute().data or []
    return sum(int(r.get("delta", 0)) for r in rows)

def _resolve_tier(client: Client, merchant_id: str, points: int) -> Optional[Dict[str, Any]]:
    """
    Resolve current tier from loyalty_tier if table exists; otherwise return None.
    """
    try:
        rows = client.table("loyalty_tier") \
            .select("*") \
            .eq("merchant_id", merchant_id) \
            .order("threshold_points") \
            .execute().data or []
        current = None
        for t in rows:
            if points >= int(t.get("threshold_points", 0)):
                current = t
            else:
                break
        return current
    except Exception:
        return None

@router.post("/accrue", tags=["loyalty"])
def accrue_points(payload: AccrueIn):
    """
    Add points to points_ledger, then return total points and current tier (if available).
    Requires the 'points_ledger' table. If missing, returns an informative error.
    """
    client = get_supabase_client()

    # Write the ledger row
    try:
        client.table("points_ledger").insert({
            "merchant_id": payload.merchant_id,
            "customer_id": payload.customer_id,
            "delta": int(payload.points),
            "reason": payload.reason,
            "ref": payload.ref or {},
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to write points_ledger: {e}")

    # Compute totals + resolve tier
    total = _sum_points(client, payload.merchant_id, payload.customer_id)
    tier = _resolve_tier(client, payload.merchant_id, total)

    return {"ok": True, "total": total, "tier": tier}

@router.get("/points/total", tags=["loyalty"])
def points_total(merchant_id: str, customer_id: str):
    """
    Return total points and current tier for a customer.
    """
    client = get_supabase_client()
    total = _sum_points(client, merchant_id, customer_id)
    tier = _resolve_tier(client, merchant_id, total)
    return {"ok": True, "total": total, "tier": tier}
