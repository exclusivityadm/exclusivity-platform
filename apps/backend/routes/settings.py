from fastapi import APIRouter
from apps.backend.services.settings import SETTINGS

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("")
def get_settings():
    return {
        "ok": True,
        "settings": SETTINGS,
    }
