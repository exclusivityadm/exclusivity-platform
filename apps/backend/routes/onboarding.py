from fastapi import APIRouter

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/start")
async def start(payload: dict):
    return {"ok": True}
