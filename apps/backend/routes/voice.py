from fastapi import APIRouter, HTTPException
import os
from apps.backend.config.voice_static import ORION_LINES, LYRIC_LINES

router = APIRouter(prefix="/voice-test", tags=["voice"])

VOICE_ENABLED = os.getenv("VOICE_ENABLED", "false").lower() == "true"


def _guard():
    if not VOICE_ENABLED:
        raise HTTPException(status_code=404, detail="Voice disabled")


@router.get("/orion")
def orion_voice():
    _guard()
    return {"ok": True, "voice": "orion", "line": ORION_LINES["greeting"]}


@router.get("/lyric")
def lyric_voice():
    _guard()
    return {"ok": True, "voice": "lyric", "line": LYRIC_LINES["greeting"]}


@router.post("/orion")
def orion_confirm():
    _guard()
    return {"ok": True, "voice": "orion", "line": ORION_LINES["confirm"]}


@router.post("/lyric")
def lyric_confirm():
    _guard()
    return {"ok": True, "voice": "lyric", "line": LYRIC_LINES["confirm"]}
