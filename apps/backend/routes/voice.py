# apps/backend/routes/voice.py
from fastapi import APIRouter
from pydantic import BaseModel
import os
import httpx
import base64

router = APIRouter()

# ✅ Corrected environment variable names to match your Render config
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ORION_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ORION")
LYRIC_VOICE_ID = os.getenv("ELEVENLABS_VOICE_LYRIC")


class VoiceRequest(BaseModel):
    speaker: str
    text: str


async def generate_voice_from_elevenlabs(text: str, voice_id: str):
    """Generate speech via ElevenLabs and return Base64-encoded MP3 audio."""
    if not ELEVENLABS_API_KEY:
        return {"error": "Missing ElevenLabs API key"}

    if not voice_id:
        return {"error": "Voice ID missing"}

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
    }

    print(f"🎤 Sending to ElevenLabs: {url}")
    print("Payload:", payload)

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)

    print(f"🔁 ElevenLabs status: {response.status_code}")
    if response.status_code != 200:
        print("⚠️ ElevenLabs non-audio response:", response.text)
        return {"error": "Voice generation failed", "details": response.text}

    audio_base64 = base64.b64encode(response.content).decode("utf-8")
    return {"audio_base64": audio_base64}


@router.post("/voice")
async def generate_voice(req: VoiceRequest):
    """Main unified route used by frontend (POST /voice)."""
    speaker = req.speaker.lower()
    text = req.text.strip()

    if not text:
        return {"error": "Text is empty"}

    if speaker == "orion":
        voice_id = ORION_VOICE_ID
    elif speaker == "lyric":
        voice_id = LYRIC_VOICE_ID
    else:
        return {"error": "Invalid speaker name"}

    return await generate_voice_from_elevenlabs(text, voice_id)
