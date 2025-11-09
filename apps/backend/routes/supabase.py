# apps/backend/routes/supabase.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/supabase", tags=["Supabase"])
async def test_supabase():
    """Temporary Supabase test endpoint."""
    return {"status": "ok", "source": "supabase route active"}
