from fastapi import APIRouter

from .services.settings import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])
service = SettingsService()


@router.get("")
async def get_settings():
    return await service.get_settings()
