import os

def is_enabled(flag: str, default: bool = False) -> bool:
    return os.getenv(flag, str(default)).lower() == "true"

SETTINGS = {
    "beta_mode": is_enabled("BETA_MODE", True),
    "loyalty_enabled": is_enabled("LOYALTY_ENABLED", True),
    "voice_enabled": is_enabled("VOICE_ENABLED", False),
    "ai_enabled": is_enabled("AI_ENABLED", False),
}
