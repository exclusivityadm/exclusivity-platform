from __future__ import annotations

from fastapi import APIRouter

from repositories.loyalty_repository import (
    LoyaltyRepository,
    create_supabase_client_from_env,
)
from health.loyalty_healthcheck import loyalty_healthcheck
from health.keepalive_scheduler import run_keepalive

router = APIRouter()


@router.get("/health")
def health_root():
    """
    Generic app health check.
    """
    return {"ok": True}


@router.get("/health/loyalty")
async def health_loyalty():
    repo = LoyaltyRepository(create_supabase_client_from_env())
    return await loyalty_healthcheck(repo)


@router.get("/health/keepalive")
async def health_keepalive():
    repo = LoyaltyRepository(create_supabase_client_from_env())
    return await run_keepalive(repo)
