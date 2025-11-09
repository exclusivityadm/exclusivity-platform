# apps/backend/routes/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["Health"])
async def health_check():
    """Basic health check endpoint for Render and uptime monitors."""
    return {"status": "ok", "service": "Exclusivity Backend"}
