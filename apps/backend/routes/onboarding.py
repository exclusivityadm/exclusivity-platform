from fastapi import APIRouter

from .services.onboarding.onboarding_service import OnboardingService


router = APIRouter(prefix="/onboarding", tags=["onboarding"])

service = OnboardingService()


@router.post("/start")
async def start_onboarding(payload: dict):
    return await service.start(payload)
