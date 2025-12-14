from __future__ import annotations
from fastapi import APIRouter, Depends

from app.repositories.loyalty_repository import LoyaltyRepository, create_supabase_client_from_env
from app.health.loyalty_healthcheck import loyalty_healthcheck
from app.health.keepalive_scheduler import run_keepalive

router = APIRouter(prefix="/health", tags=["health"])


def get_repo() -> LoyaltyRepository:
    sb = create_supabase_client_from_env()
    return LoyaltyRepository(sb)


@router.get("/loyalty")
async def loyalty_health(repo: LoyaltyRepository = Depends(get_repo)):
    return await loyalty_healthcheck(repo)


@router.get("/keepalive")
async def keepalive(repo: LoyaltyRepository = Depends(get_repo)):
    return await run_keepalive(repo)
