# main.py
# -------------------------------------------------
# Exclusivity Backend - Voice Service (ElevenLabs Only)
# -------------------------------------------------
import os
import asyncio
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
import httpx

# ------- Config & App -------
ENV = os.getenv("ENVIRONMENT", "production")
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "*")

app = FastAPI(title="Exclusivity Backend", version="6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOW_ORIGINS.split(",")] if ALLOW_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------- Health -------
@app.get("/", response_class=PlainTextResponse)
async def root():
    return "OK - Exclusivity Backend v6.0"

@app.get("/health", response_class=JSONResponse)
async def health():
    return {"status": "ok", "version": "6.0"}

# ------- Models -------
Speaker = Literal["orion", "lyric"]

class SpeakRequest(BaseModel):
    text: str
    speaker: Speaker = "orion"
    format: Literal["mp3", "wav"] = "mp3"

# ------- ElevenLabs Voice Settings -------
# Replace these IDs with your actual ElevenLabs voice IDs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ORION = "CGhTDelcmik3E17Nrvcf"
ELEVENLABS_VOICE_LYRIC = "rujGCruvEqncqHTi6l0q"

def get_voice_id(speaker: Speaker) -> str:
    if speaker == "orion":
        return ELEVENLABS_VOICE_ORION
    elif speaker == "lyric":
        return ELEVENLABS_VOICE_LYRIC
    raise HTTPException(status_code=400, detail=f"Unknown speaker: {speaker}")

def media_type(fmt: str) -> str:
    return "audio/mpeg" if fmt == "mp3" else "audio/wav"

# ------- ElevenLabs TTS -------
async def elevenlabs_tts(text: str, voice_id: str, fmt: str) -> bytes:
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not configured.")
    if not voice_id:
        raise HTTPException(status_code=500, detail="Missing ElevenLabs voice ID.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Accept": "audio/mpeg" if fmt == "mp3" else "audio/wav",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.75,
            "style": 0.2,
            "use_speaker_boost": True
        }
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            print(f"⚠️ ElevenLabs error {r.status_code}: {r.text}")
            raise HTTPException(status_code=500, detail=f"ElevenLabs error {r.status_code}: {r.text}")
        return r.content

# ------- Routes -------
@app.post("/voice/speak")
async def speak(req: SpeakRequest):
    fmt = req.format
    voice_id = get_voice_id(req.speaker)
    ct = media_type(fmt)

    start = asyncio.get_event_loop().time()
    data = await elevenlabs_tts(req.text, voice_id, fmt)
    duration = round(asyncio.get_event_loop().time() - start, 2)

    print(f"[voice] {req.speaker.upper()} → ElevenLabs ({fmt}) [{len(data)} bytes, {duration}s]")
    return StreamingResponse(iter([data]), media_type=ct)

# ------- Startup -------
@app.on_event("startup")
async def on_startup():
    print("✅ Exclusivity Backend voice service started (ElevenLabs Only)")
    print(f"   Orion → {ELEVENLABS_VOICE_ORION}")
    print(f"   Lyric → {ELEVENLABS_VOICE_LYRIC}")
