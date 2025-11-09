from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check():
    """Simple health endpoint to verify backend is live."""
    data = {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "backend": "Exclusivity Backend Operational",
    }
    return JSONResponse(content=data)
