# apps/backend/routes/orion.py

from enum import Enum
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import os
import httpx
import base64


# -----------------------------
# Persona Enum (REQUIRED BY AI)
# -----------------------------
class Persona(str, Enum):
    ORION = "orion"
    LYRIC = "lyric"


# -----------------------------
# Orion Voice Router
# -----------------------------
router = APIRouter()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ORION_VOICE_ID = os.getenv("ORION_VOICE_ID")


class TextIn(BaseModel):
    text: str | None = None  # if None -> default phrase


def _default_text():
    return "Hello, this is Orion — your Exclusivity copilot online and ready."


@router.post("/speak")
async def orion_speak(body: TextIn):
    if not ELEVENLABS_API_KEY or not ORION_VOICE_ID:
        return JSONResponse(
            {"error": "Missing ElevenLabs API key or ORION_VOICE_ID"},
            status_code=500,
        )

    text = (body.text or _default_text()).strip()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ORION_VOICE_ID}"
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

    async with httpx.AsyncClient(timeout=None) as client:
        r = await client.post(url, headers=headers, json=payload)

    if r.status_code != 200:
        return JSONResponse(
            {"error": "Voice generation failed", "details": r.text},
            status_code=500,
        )

    b64 = base64.b64encode(r.content).decode("utf-8")
    return JSONResponse({"audio_base64": b64})


@router.post("/stream")
async def orion_stream(body: TextIn):
    if not ELEVENLABS_API_KEY or not ORION_VOICE_ID:
        return JSONResponse(
            {"error": "Missing ElevenLabs API key or ORION_VOICE_ID"},
            status_code=500,
        )

    text = (body.text or _default_text()).strip()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ORION_VOICE_ID}/stream"
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

    async with httpx.AsyncClient(timeout=None) as client:
        upstream = await client.post(url, headers=headers, json=payload)
        if upstream.status_code != 200:
            return JSONResponse(
                {"error": "Voice generation failed", "details": upstream.text},
                status_code=500,
            )

        async def _gen():
            async for chunk in upstream.aiter_bytes():
                if chunk:
                    yield chunk

        return StreamingResponse(_gen(), media_type="audio/mpeg")
