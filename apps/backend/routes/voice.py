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

@router.post("/")
async def generate_voice(req: VoiceRequest):
    if not ELEVENLABS_API_KEY:
        return {"error": "Missing ElevenLabs API key"}

    if req.speaker.lower() == "orion":
        voice_id = ORION_VOICE_ID
    elif req.speaker.lower() == "lyric":
        voice_id = LYRIC_VOICE_ID
    else:
        return {"error": "Invalid speaker name"}

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"text": req.text, "model_id": "eleven_multilingual_v2"}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)

    if response.status_code != 200:
        return {"error": "Voice generation failed", "details": response.text}

    return {"audio_url": response.json().get("url", "")}
