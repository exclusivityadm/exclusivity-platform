# apps/backend/routes/voice.py
from fastapi import APIRouter, Request
from pydantic import BaseModel
import os
import httpx

router = APIRouter()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ORION_VOICE_ID = os.getenv("ORION_VOICE_ID")
LYRIC_VOICE_ID = os.getenv("LYRIC_VOICE_ID")


class VoiceRequest(BaseModel):
    speaker: str
    text: str


async def call_elevenlabs_api(text: str, voice_id: str):
    """Helper to send text-to-speech to ElevenLabs"""
    if not ELEVENLABS_API_KEY:
        return {"error": "Missing ElevenLabs API key"}

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"text": text, "model_id": "eleven_multilingual_v2"}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)

    if response.status_code != 200:
        return {
            "error": "Voice generation failed",
            "status_code": response.status_code,
            "details": response.text,
        }

    return {"audio_url": response.json().get("url", "")}


@router.post("/")
async def generate_voice(req: VoiceRequest):
    """POST /voice — expects { speaker: 'orion'|'lyric', text: 'string' }"""
    speaker = req.speaker.lower()
    text = req.text

    if speaker == "orion":
        voice_id = ORION_VOICE_ID
    elif speaker == "lyric":
        voice_id = LYRIC_VOICE_ID
    else:
        return {"error": f"Invalid speaker '{req.speaker}'"}

    return await call_elevenlabs_api(text, voice_id)
