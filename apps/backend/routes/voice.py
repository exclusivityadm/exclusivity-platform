from fastapi import APIRouter
from pydantic import BaseModel
import os
import httpx
import base64

router = APIRouter()

# --- Environment Variables ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# ✅ Use only the two verified variable names present in Render
ORION_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ORION") or os.getenv("AI_VOICE_ORION")
LYRIC_VOICE_ID = os.getenv("ELEVENLABS_VOICE_LYRIC") or os.getenv("AI_VOICE_LYRIC")

class VoiceRequest(BaseModel):
    speaker: str
    text: str

async def generate_voice_from_elevenlabs(text: str, voice_id: str):
    """Generate speech via ElevenLabs and return Base64-encoded MP3 audio."""
    if not ELEVENLABS_API_KEY:
        return {"error": "Missing ELEVENLABS_API_KEY"}

    if not voice_id:
        return {"error": "Missing ElevenLabs voice ID"}

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        return {
            "error": "Voice generation failed",
            "status_code": response.status_code,
            "details": response.text,
        }

    # Convert audio binary to Base64
    audio_base64 = base64.b64encode(response.content).decode("utf-8")
    return {"audio_base64": audio_base64}


@router.post("/")
async def generate_voice(req: VoiceRequest):
    """Main voice synthesis endpoint (POST /voice)."""
    speaker = req.speaker.lower().strip()
    text = req.text.strip()

    if not text:
        return {"error": "Text is empty"}

    if speaker == "orion":
        voice_id = ORION_VOICE_ID
    elif speaker == "lyric":
        voice_id = LYRIC_VOICE_ID
    else:
        return {"error": f"Invalid speaker name: {speaker}"}

    return await generate_voice_from_elevenlabs(text, voice_id)


@router.get("/test")
async def voice_test():
    """Verify ElevenLabs configuration is correctly loaded."""
    return {
        "ELEVENLABS_API_KEY": "set" if ELEVENLABS_API_KEY else None,
        "ORION_VOICE_ID": ORION_VOICE_ID,
        "LYRIC_VOICE_ID": LYRIC_VOICE_ID,
    }
