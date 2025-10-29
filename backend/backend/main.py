import os
import asyncio
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel
import httpx
import json

# ==============================================================
#  CONFIG & APP
# ==============================================================
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

# ==============================================================
#  HEALTH ENDPOINTS
# ==============================================================
@app.get("/", response_class=PlainTextResponse)
async def root():
    return "OK - Exclusivity Backend v6.0"

@app.get("/health", response_class=JSONResponse)
async def health():
    return {"status": "ok", "version": "6.0"}

# ==============================================================
#  MODELS
# ==============================================================
Speaker = Literal["orion", "lyric"]

class SpeakRequest(BaseModel):
    text: str
    speaker: Speaker = "orion"
    format: Literal["mp3", "wav"] = "mp3"

# ==============================================================
#  VOICE UTILITIES
# ==============================================================
async def elevenlabs_tts(text: str, voice_id: str, fmt: str) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY missing")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
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
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg" if fmt == "mp3" else "audio/wav",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text}")
        return r.content

async def openai_tts(text: str, voice: str, fmt: str) -> bytes:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    url = "https://api.openai.com/v1/audio/speech"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "voice": voice,
        "input": text,
        "format": "mp3" if fmt == "mp3" else "wav"
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"OpenAI TTS error {r.status_code}: {r.text}")
        return r.content

def pick_voice_ids(speaker: str):
    if speaker == "orion":
        return (
            os.getenv("ELEVENLABS_VOICE_ORION"),
            os.getenv("OPENAI_VOICE_ORION", "alloy")
        )
    else:
        return (
            os.getenv("ELEVENLABS_VOICE_LYRIC"),
            os.getenv("OPENAI_VOICE_LYRIC", "verse")
        )

# ==============================================================
#  SPEAK ENDPOINT
# ==============================================================
@app.post("/voice/speak")
async def speak(req: SpeakRequest):
    eleven_id, openai_voice = pick_voice_ids(req.speaker)
    data: Optional[bytes] = None
    content_type = "audio/mpeg" if req.format == "mp3" else "audio/wav"

    # Primary: ElevenLabs
    if os.getenv("ELEVENLABS_API_KEY") and eleven_id:
        try:
            data = await elevenlabs_tts(req.text, eleven_id, req.format)
        except Exception:
            data = None

    # Fallback: OpenAI
    if data is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=500, detail="No TTS providers available (configure ElevenLabs or OpenAI).")
        data = await openai_tts(req.text, openai_voice, req.format)

    return StreamingResponse(iter([data]), media_type=content_type)

# ==============================================================
#  TIERS ENDPOINT (Read-Only)
# ==============================================================
def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return None

@app.get("/tiers", response_class=JSONResponse)
async def get_tiers():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_dir, "config")
    backend_path = os.path.join(config_dir, "tiers.json")
    ui_path = os.path.join(config_dir, "tiers_ui.json")

    backend_data = load_json(backend_path)
    ui_data = load_json(ui_path)

    if not backend_data or not ui_data:
        raise HTTPException(status_code=500, detail="Tier configuration not found or invalid.")

    return {
        "version": backend_data.get("version", "1.0"),
        "tiers_backend": backend_data.get("tiers", []),
        "tiers_ui": ui_data.get("tiers", [])
    }

# ==============================================================
#  SUPABASE KEEPALIVE (Optional)
# ==============================================================
async def supabase_keepalive():
    supa_url = os.getenv("SUPABASE_URL")
    supa_key = os.getenv("SUPABASE_ANON_KEY")
    if not supa_url or not supa_key:
        return
    health_url = f"{supa_url.rstrip('/')}/auth/v1/health"
    headers = {"apikey": supa_key}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.get(health_url, headers=headers)
    except Exception:
        pass

async def keepalive_loop():
    while True:
        await supabase_keepalive()
        await asyncio.sleep(6 * 60 * 60)  # every 6 hours

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(keepalive_loop())
