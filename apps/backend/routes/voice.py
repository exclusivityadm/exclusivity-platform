# apps/backend/routes/voice.py
from fastapi import APIRouter
from pydantic import BaseModel
import os
import httpx
import base64
import binascii

router = APIRouter()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ORION_VOICE_ID = os.getenv("ORION_VOICE_ID")
LYRIC_VOICE_ID = os.getenv("LYRIC_VOICE_ID")


class VoiceRequest(BaseModel):
    speaker: str
    text: str


async def generate_voice_from_elevenlabs(text: str, voice_id: str):
    """Generate speech via ElevenLabs and return Base64-encoded MP3 audio, with debug logs."""
    if not ELEVENLABS_API_KEY:
        print("❌ Missing ELEVENLABS_API_KEY")
        return {"error": "Missing ElevenLabs API key"}

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
    print(f"Payload: {payload}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)

    print(f"🔁 ElevenLabs status: {response.status_code}")
    print(f"🔁 ElevenLabs headers: {dict(response.headers)}")

    # Try to print a short digest of response data safely
    try:
        if response.headers.get("content-type", "").startswith("audio"):
            print(f"✅ Binary audio response detected, {len(response.content)} bytes received")
        else:
            # likely JSON (error or rate limit)
            snippet = response.text[:1000]
            print(f"⚠️ ElevenLabs non-audio response: {snippet}")
    except Exception as e:
        print(f"⚠️ Error printing ElevenLabs response: {e}")

    if response.status_code != 200:
        return {
            "error": "Voice generation failed",
            "status_code": response.status_code,
            "details": response.text,
        }

    if not response.content:
        print("⚠️ ElevenLabs returned an empty body")
        return {"error": "Empty audio response"}

    try:
        audio_base64 = base64.b64encode(response.content).decode("utf-8")
        return {"audio_base64": audio_base64}
    except binascii.Error as e:
        print(f"⚠️ Base64 encoding failed: {e}")
        return {"error": "Failed to encode audio"}


@router.post("/voice")
async def generate_voice(req: VoiceRequest):
    """Unified route used by frontend (POST /voice)."""
    speaker = req.speaker.lower().strip()
    text = req.text.strip()

    if not text:
        return {"error": "Text is empty"}

    if speaker == "orion":
        voice_id = ORION_VOICE_ID
    elif speaker == "lyric":
        voice_id = LYRIC_VOICE_ID
    else:
        return {"error": "Invalid speaker name"}

    result = await generate_voice_from_elevenlabs(text, voice_id)
    return result
