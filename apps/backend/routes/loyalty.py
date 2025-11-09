# =====================================================
# 🪙 Exclusivity Backend - Loyalty Routes
# =====================================================

from fastapi import APIRouter
import os
from supabase import create_client, Client

router = APIRouter()

# -----------------------------------------------------
# 🔧 Helper: Create Supabase client
# -----------------------------------------------------
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Missing Supabase credentials in environment.")
    return create_client(url, key)

# -----------------------------------------------------
# 🩺 Health & Database Connectivity Test
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
# 📊 Placeholder Loyalty Endpoints (expand later)
# -----------------------------------------------------
@router.get("/tiers", tags=["loyalty"])
def get_loyalty_tiers():
    """
    Placeholder endpoint for tier retrieval.
    Will later query Supabase tables for live tier data.
    """
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
