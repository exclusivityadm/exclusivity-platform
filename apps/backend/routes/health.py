from __future__ import annotations

from fastapi import APIRouter

from repositories.loyalty_repository import (
    LoyaltyRepository,
    create_supabase_client_from_env,
)
from health.loyalty_healthcheck import loyalty_healthcheck
from health.keepalive_scheduler import run_keepalive

router = APIRouter()


@router.get("")
def health_root():
    """
    Generic app health check.
    Mounted at /health
    """
    return {"ok": True}


@router.get("/loyalty")
async def health_loyalty():
    """
    Mounted at /health/loyalty
    """
    repo = LoyaltyRepository(create_supabase_client_from_env())
    return await loyalty_healthcheck(repo)


@router.get("/keepalive")
async def health_keepalive():
    """
    Mounted at /health/keepalive
    """
    repo = LoyaltyRepository(create_supabase_client_from_env())
    return await run_keepalive(repo)
