# apps/backend/routes/voice.py
from fastapi import APIRouter
from pydantic import BaseModel
import os
import httpx
import base64

router = APIRouter()

# Environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ORION_VOICE_ID = os.getenv("ORION_VOICE_ID")
LYRIC_VOICE_ID = os.getenv("LYRIC_VOICE_ID")


# Request model
class VoiceRequest(BaseModel):
    speaker: str
    text: str


@router.post("/")
async def generate_voice(req: VoiceRequest):
    """Unified route for generating voice audio for Orion or Lyric."""
    if not ELEVENLABS_API_KEY:
        return {"error": "Missing ElevenLabs API key"}

    # Select the correct voice ID
    speaker
