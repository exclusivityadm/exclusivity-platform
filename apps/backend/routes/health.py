from __future__ import annotations

from fastapi import APIRouter

from .health_checks.loyalty_healthcheck import loyalty_healthcheck
from .health_checks.keepalive_scheduler import run_keepalive

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_root():
    return {"ok": True}


@router.get("/loyalty")
async def health_loyalty():
    """
    Verifies loyalty subsystem:
    - Supabase connectivity
    - Required tables
    - RLS viability
    """
    return await loyalty_healthcheck()


@router.get("/keepalive")
async def health_keepalive():
    """
    Triggers non-destructive keepalive logic
    (Supabase, Render, Vercel pings if configured)
    """
    await run_keepalive()
    return {"ok": True}
