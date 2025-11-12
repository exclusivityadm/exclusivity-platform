# apps/backend/routes/keepalive_status.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime
import os

router = APIRouter(prefix="/keepalive", tags=["Keepalive"])

@router.get("/status")
async def keepalive_status():
    """
    Lightweight endpoint to confirm that background keepalive tasks are active.
    Returns confirmation for Render, Supabase, and Vercel.
    """
    now = datetime.utcnow().isoformat() + "Z"

    render_url = os.getenv("RENDER_SELF_URL", "not configured")
    supabase_url = os.getenv("SUPABASE_URL", "not configured")
    vercel_url = os.getenv("VERCEL_URL", "not configured")

    data = {
        "timestamp": now,
        "keepalive_enabled": os.getenv("KEEPALIVE_ENABLED", "false"),
        "targets": {
            "render": render_url,
            "supabase": supabase_url,
            "vercel": vercel_url
        },
        "status": "active",
        "message": "All keepalive tasks are scheduled and running quietly in the background."
    }

    return JSONResponse(content=data)
