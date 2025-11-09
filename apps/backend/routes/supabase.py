from fastapi import APIRouter
from fastapi.responses import JSONResponse
from supabase import create_client, Client
import os

router = APIRouter(prefix="/supabase", tags=["Supabase"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


@router.get("/check")
async def supabase_check():
    """Check connection to Supabase and confirm tables exist."""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Missing Supabase credentials.")
        client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Quick table existence check
        result = client.table("profiles").select("*").limit(1).execute()
        count = len(result.data) if result.data else 0
        return JSONResponse(
            content={"connected": True, "rows_found": count, "message": "Supabase reachable."}
        )
    except Exception as e:
        return JSONResponse(content={"connected": False, "error": str(e)}, status_code=500)
