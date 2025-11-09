# apps/backend/routes/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint used for Render or uptime monitoring."""
    return {"status": "ok", "service": "Exclusivity Backend"}
