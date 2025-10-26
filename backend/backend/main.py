# main.py
import os
import httpx
from typing import Optional, Literal, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import asyncio

# -------------------------------------------------
# FastAPI App Setup
# -------------------------------------------------
app = FastAPI(title="LUX Loyalty Voice Service")

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
    provider: Optional[Literal["auto", "elevenlabs", "openai"]] = "auto"

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def pick_voice_ids(speaker: Speaker) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns the (ElevenLabs voice ID, OpenAI voice alias)
    for the given speaker.
    """
    if speaker == "orion":
        return (
            os.getenv("ELEVENLABS_VOICE_ORION"),
            os.getenv("OPENAI_VOICE_ORION"),
        )
    elif speaker == "lyric":
        return (
            os.getenv("ELEVENLABS_VOICE_LYRIC"),
            os.getenv("OPENAI_VOICE_LYRIC"),
        )
    else:
        raise ValueError(f"Unknown speaker: {speaker}")

def media_type(fmt: str) -> str:
    return "audio/mpeg" if fmt == "mp3" else "audio/wav"

# -------------------------------------------------
# Validation
# -------------------------------------------------
def validate_voice_map():
    el_orion = os.getenv("ELEVENLABS_VOICE_ORION")
    el_lyric = os.getenv("ELEVENLABS_VOICE_LYRIC")
    oa_orion = os.getenv("OPENAI_VOICE_ORION")
    oa_lyric = os.getenv("OPENAI_VOICE_LYRIC")

    if el_orion and el_lyric and el_orion == el_lyric:
        raise RuntimeError("ELEVENLABS voice IDs for Orion and Lyric must differ.")
    if oa_orion and oa_lyric and oa_orion == oa_lyric:
        raise RuntimeError("OPENAI voice aliases for Orion and Lyric must differ.")

    print(
        f"[voice-map] ORION → (EL:{el_orion or '-'}) / (OA:{oa_orion or '-'}) | "
        f"LYRIC → (EL:{el_lyric or '-'}) / (OA:{oa_lyric or '-'})"
    )

validate_voice_map()

# -------------------------------------------------
# TTS Providers
# -------------------------------------------------
async def elevenlabs_tts(text: str, voice_id: str, fmt: str) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": os.getenv("ELEVENLABS_API_KEY"),
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"ElevenLabs error {resp.status_code}: {resp.text}",
            )
        return resp.content

async def openai_tts(text: str, voice: str, fmt: str) -> bytes:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = await client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
        format=fmt,
    )
    return await response.read()

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "service": "LUX Loyalty Voice API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/voice/speak")
async def speak(req: SpeakRequest):
    start = asyncio.get_event_loop().time()
    fmt = req.format
    content_type = media_type(fmt)
    el_voice, oa_voice = pick_voice_ids(req.speaker)

    # Force provider if specified
    provider = req.provider or "auto"
    data = None

    try:
        if provider == "elevenlabs":
            if not (os.getenv("ELEVENLABS_API_KEY") and el_voice):
                raise HTTPException(400, detail="ElevenLabs not configured.")
            data = await elevenlabs_tts(req.text, el_voice, fmt)

        elif provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise HTTPException(400, detail="OpenAI not configured.")
            data = await openai_tts(req.text, oa_voice, fmt)

        else:  # auto
            if os.getenv("ELEVENLABS_API_KEY") and el_voice:
                try:
                    data = await elevenlabs_tts(req.text, el_voice, fmt)
                except Exception as e:
                    print(f"[warn] ElevenLabs failed, falling back: {e}")
                    data = None

            if data is None:
                if not os.getenv("OPENAI_API_KEY"):
                    raise HTTPException(
                        500,
                        detail="No TTS providers available (configure ElevenLabs or OpenAI).",
                    )
                data = await openai_tts(req.text, oa_voice, fmt)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    duration = round(asyncio.get_event_loop().time() - start, 2)
    print(
        f"[voice] {req.speaker.upper()} via {provider} → {fmt} ({len(data)} bytes in {duration}s)"
    )
    return StreamingResponse(iter([data]), media_type=content_type)

# -------------------------------------------------
# Optional: lightweight keepalive to Supabase or other
# -------------------------------------------------
@app.on_event("startup")
async def startup():
    print("Service started and ready for voice synthesis.")
