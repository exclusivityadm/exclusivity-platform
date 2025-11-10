from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os

# ❌ Remove prefix here — it’s already set in main.py
router = APIRouter(tags=["Health"])

@router.get("/")
async def health_check():
    """Simple health endpoint to verify backend is live."""
    data = {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "backend": "Exclusivity Backend Operational",
    }
    return JSONResponse(content=data)
