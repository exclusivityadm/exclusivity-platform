from fastapi import APIRouter
from ..config import env
router = APIRouter()

@router.get("")
def get_settings():
    return {
        "app_name": env("APP_NAME","Exclusivity"),
        "env": env("APP_ENV","production"),
        "voice_enabled": env("FEATURE_VOICE_ENABLED","true") == "true",
        "aura_enabled": env("FEATURE_AURA_ENABLED","true") == "true",
    }
