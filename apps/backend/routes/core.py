from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from apps.backend.services.core_service import (
    bootstrap,
    me,
    advance_onboarding,
    health_core,
    CoreError,
)

router = APIRouter(prefix="/core", tags=["core"])


@router.post("/bootstrap")
async def core_bootstrap(request: Request):
    try:
        return bootstrap(request)
    except CoreError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.message})


@router.get("/me")
async def core_me(request: Request):
    try:
        return me(request)
    except CoreError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.message})


@router.post("/onboarding/advance")
async def core_onboarding_advance(request: Request):
    try:
        return advance_onboarding(request)
    except CoreError as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.message})


@router.get("/health")
async def core_health():
    return health_core()
