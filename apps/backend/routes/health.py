from fastapi import APIRouter

from .health_checks.loyalty_healthcheck import loyalty_healthcheck
from .health_checks.keepalive_scheduler import run_keepalive


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_root():
    return {"ok": True}


@router.get("/loyalty")
async def health_loyalty():
    return await loyalty_healthcheck()


@router.get("/keepalive")
async def health_keepalive():
    await run_keepalive()
    return {"ok": True}
