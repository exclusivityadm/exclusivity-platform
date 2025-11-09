# apps/backend/routes/voice.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import base64
import io
import os
import requests

router = APIRouter(prefix="/voice", tags=["Voice"])

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# simple request model if needed later
class VoiceRequest(BaseModel):
    text: str | None = "System check complete. The Exclusivity voice module is active."

def synthesize_elevenlabs(speaker: str, text: str) -> bytes:
    """Call ElevenLabs TTS and return raw audio bytes."""
    voice_id = os.getenv(f"{speaker.upper()}_VOICE_ID")  # e.g., ORION_VOICE_ID, LYRIC_VOICE_ID
    if not (ELEVEN_API_KEY and voice_id):
        raise RuntimeError("Missing ElevenLabs credentials")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
    }

    r = requests.post(url, headers=headers, json=payload)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text}")
    return r.content


@router.get("/{speaker}")
async def generate_voice(speaker: str):
    """Return playable audio for Orion or Lyric."""
    if speaker.lower() not in ["orion", "lyric"]:
        raise HTTPException(status_code=404, detail="Unknown speaker")

    try:
        audio_bytes = synthesize_elevenlabs(speaker, f"Hello, I am {speaker.capitalize()}. The system is active.")
        # Stream the mp3 directly so browser can play it
        return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")

    except Exception as e:
        # also return base64 fallback for debugging
        err = str(e)
        b64 = ""
        try:
            b64 = base64.b64encode(audio_bytes).decode() if "audio_bytes" in locals() else ""
        except Exception:
            pass
        return JSONResponse(
            content={"speaker": speaker, "error": err, "audio_base64": b64},
            status_code=500,
        )
