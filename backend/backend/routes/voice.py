# backend/backend/routes/voice.py
import io
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from pydantic import BaseModel

from ..utils.voice_router import get_character_config, pick_openai_voice_for_gender

router = APIRouter(prefix="/voice", tags=["voice"])

# ---- Config defaults (safe with your requirements) ----
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

class TTSRequest(BaseModel):
    character: str  # "orion" | "lyric"
    text: str

async def synth_elevenlabs(text: str, voice_id: str) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not api_key:
        raise RuntimeError("Missing ELEVENLABS_API_KEY")
    if not voice_id:
        raise RuntimeError("Missing ElevenLabs voice_id")

    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        # You can tune these later
        "model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
        "voice_settings": {
            "stability": float(os.getenv("ELEVENLABS_STABILITY", "0.5")),
            "similarity_boost": float(os.getenv("ELEVENLABS_SIMILARITY", "0.75")),
        },
        "optimize_streaming_latency": int(os.getenv("ELEVENLABS_STREAM_LATENCY", "3")),
        "output_format": "mp3_44100_128",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(ELEVEN_URL.format(voice_id=voice_id), headers=headers, json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:200]}")
        return r.content

async def synth_openai(text: str, gender: str, explicit_voice: str | None = None) -> bytes:
    """
    Uses OpenAI TTS as fallback (or primary if you force it).
    Requires OPENAI_API_KEY + compatible model (default gpt-4o-mini-tts).
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    voice_name = (explicit_voice or "").strip() or pick_openai_voice_for_gender(gender)
    # Generate as a single MP3 blob
    speech = client.audio.speech.create(
        model=os.getenv("OPENAI_TTS_MODEL", OPENAI_TTS_MODEL),
        voice=voice_name,
        input=text,
        format="mp3"
    )
    return speech.read()  # bytes

@router.post("/tts", response_class=StreamingResponse)
async def tts(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    cfg = get_character_config(req.character)

    # Attempt preferred engine first, then fallback
    engines = [cfg.engine, "openai" if cfg.engine == "elevenlabs" else "elevenlabs"]

    last_error: str | None = None
    for engine in engines:
        try:
            if engine == "elevenlabs":
                # If missing Eleven voice id, skip to next engine
                if not os.getenv("ELEVENLABS_API_KEY") or not cfg.voice_id:
                    raise RuntimeError("ElevenLabs not configured or missing voice id.")
                audio_bytes = await synth_elevenlabs(req.text, cfg.voice_id)
            else:
                # OpenAI (explicit voice may be present in cfg.voice_id if not an 11L id)
                if not os.getenv("OPENAI_API_KEY"):
                    raise RuntimeError("OpenAI not configured.")
                audio_bytes = await synth_openai(req.text, cfg.gender, cfg.voice_id)

            # Success -> stream as mp3
            return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")
        except Exception as e:
            last_error = str(e)
            continue

    raise HTTPException(status_code=502, detail=f"TTS engines failed. Last error: {last_error or 'unknown'}")
