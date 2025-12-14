from __future__ import annotations

from fastapi import APIRouter

from apps.backend.repositories.loyalty_repository import (
    LoyaltyRepository,
    create_supabase_client_from_env,
)
from apps.backend.health_checks.loyalty_healthcheck import loyalty_healthcheck
from apps.backend.health_checks.keepalive_scheduler import run_keepalive

router = APIRouter()


@router.get("")
def health_root():
    return {"ok": True}


@router.get("/loyalty")
async def health_loyalty():
    repo = LoyaltyRepository(create_supabase_client_from_env())
    return await loyalty_healthcheck(repo)


@router.get("/keepalive")
async def health_keepalive():
    repo = LoyaltyRepository(create_supabase_client_from_env())
    return await run_keepalive(repo)
