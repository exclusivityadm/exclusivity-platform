# apps/backend/routes/voice.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/voice", tags=["Voice"])
async def test_voice():
    """Placeholder route for voice/TTS operations."""
    return {"status": "ok", "source": "voice route active"}
