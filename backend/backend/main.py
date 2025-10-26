# main.py
# -------------------------------------------------
# LUX Loyalty Voice Service (ElevenLabs Only)
# -------------------------------------------------
import os
import httpx
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import asyncio

# -------------------------------------------------
# Configuration
# -------------------------------------------------
# Hardcode your ElevenLabs voice IDs here
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ORION = "CGhTDelcmik3E17Nrvcf"   # e.g., "a1b2c3d4e5f6..."
ELEVENLABS_VOICE_LYRIC = "rujGCruvEqncqHTi6l0q" # e.g., "z9y8x7w6v5u4..."

if not ELEVENLABS_API_KEY:
    raise RuntimeError("Missing ELEVENLABS_API_KEY — please set your API key.")

# -------------------------------------------------
# FastAPI setup
# -------------------------------------------------
app = FastAPI(title="LUX Loyalty Voice API (ElevenLabs Only)")

allow_origins = os.getenv("ALLOW_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# Models
# -------------------------------------------------
Speaker = Literal["orion", "lyric"]

class SpeakRequest(BaseModel):
    text: str
    speaker: Speaker = "orion"
    format: Literal["mp3", "wav"] = "mp3"

# -------------------------------------------------
# Helper functions
# -------------------------------------------------
def get_voice_id(speaker: Speaker) -> str:
    if speaker == "orion":
        return ELEVENLABS_VOICE_ORION
    elif speaker == "lyric":
        return ELEVENLABS_VOICE_LYRIC
    else:
        raise HTTPException(status_code=400, detail=f"Unknown speaker '{speaker}'.")

def media_type(fmt: str) -> str:
    return "audio/mpeg" if fmt == "mp3" else "audio/wav"

# -------------------------------------------------
# ElevenLabs TTS
# -------------------------------------------------
async def elevenlabs_tts(text: str, voice_id: str, fmt: str) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"ElevenLabs error {response.status_code}: {response.text}",
            )
        return response.content

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "service": "LUX Loyalty Voice API (ElevenLabs Only)"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/voice/speak")
async def speak(req: SpeakRequest):
    fmt = req.format
    content_type = media_type(fmt)
    voice_id = get_voice_id(req.speaker)

    if not voice_id:
        raise HTTPException(
            status_code=500, detail=f"No ElevenLabs voice ID for {req.speaker}"
        )

    start = asyncio.get_event_loop().time()
    try:
        data = await elevenlabs_tts(req.text, voice_id, fmt)
        duration = round(asyncio.get_event_loop().time() - start, 2)
        print(
            f"[voice] {req.speaker.upper()} → ElevenLabs | {fmt.upper()} | {len(data)} bytes in {duration}s"
        )
        return StreamingResponse(iter([data]), media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ElevenLabs failed: {e}")

# -------------------------------------------------
# Startup
# -------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("✅ LUX Loyalty Voice Service started (ElevenLabs Only)")
    print(f"   Orion → {ELEVENLABS_VOICE_ORION}")
    print(f"   Lyric → {ELEVENLABS_VOICE_LYRIC}")
