# apps/backend/routes/voice.py
from fastapi import APIRouter, Request
from pydantic import BaseModel
import os
import httpx
import base64

router = APIRouter()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ORION_VOICE_ID = os.getenv("ORION_VOICE_ID")
LYRIC_VOICE_ID = os.getenv("LYRIC_VOICE_ID")

class VoiceRequest(BaseModel):
    speaker: str
    text: str

async def generate_voice_from_elevenlabs(text: str, voice_id: str):
    """Generate speech via ElevenLabs and return Base64-encoded audio."""
    if not ELEVENLABS_API_KEY:
        return {"error": "Missing ElevenLabs API key"}

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",  # try "eleven_turbo_v2" if needed
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)

    if response.status_code != 200:
        return {"error": "Voice generation failed", "details": response.text}

    # ✅ Convert binary MP3 audio to Base64 so frontend can play it
    audio_base64 = base64.b64encode(response.content).decode("utf-8")
    return {"audio_base64": audio_base64}

@router.post("/voice")
async def generate_voice(req: VoiceRequest):
    """Main unified route used by frontend (POST /voice)."""
    speaker = req.speaker.lower()
    text = req.text

    if speaker == "orion":
        voice_id = ORION_VOICE_ID
    elif speaker == "lyric":
        voice_id = LYRIC_VOICE_ID
    else:
        return {"error": "Invalid speaker name"}

    return await generate_voice_from_elevenlabs(text, voice_id)
