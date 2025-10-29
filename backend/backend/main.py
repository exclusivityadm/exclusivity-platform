import os
import asyncio
import json
import httpx
from typing import Optional, Literal
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ==============================================================
#  APP INITIALIZATION
# ==============================================================

app = FastAPI(title="Exclusivity Backend", version="6.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================
#  LOGGING HELPER
# ==============================================================

def log(msg: str, level: str = "INFO"):
    print(f"[{datetime.utcnow().isoformat()}Z] [{level}] {msg}")

# ==============================================================
#  ENVIRONMENT CHECK
# ==============================================================

def check_env_keys():
    required = ["ELEVENLABS_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY"]
    for key in required:
        if not os.getenv(key):
            log(f"⚠️ Environment key missing: {key}", "WARN")

# ==============================================================
#  HEALTH & ROOT ENDPOINTS
# ==============================================================

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "OK - Exclusivity Backend v6.3"

@app.get("/health", response_class=JSONResponse)
async def health():
    return {
        "status": "ok",
        "version": "6.3",
        "environment": os.getenv("ENVIRONMENT", "production")
    }

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
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    url = "https://api.openai.com/v1/audio/speech"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        "voice": voice,
        "input": text,
        "format": fmt
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
        except Exception as e:
            log(f"ElevenLabs failed: {e}", "WARN")
            data = None

    # Fallback: OpenAI
    if data is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=500, detail="No TTS providers available.")
        data = await openai_tts(req.text, openai_voice, req.format)

    return StreamingResponse(iter([data]), media_type=content_type)

# ==============================================================
#  CONFIG + MANIFEST UTILITIES
# ==============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
MANIFEST_PATH = os.path.join(CONFIG_DIR, "tiers_manifest.json")

def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error loading {path}: {e}", "WARN")
        return None

def load_manifest():
    if not os.path.exists(MANIFEST_PATH):
        return None
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Could not read manifest: {e}", "WARN")
        return None

# Cache setup
TIERS_CACHE = {
    "backend": load_json(os.path.join(CONFIG_DIR, "tiers.json")),
    "ui": load_json(os.path.join(CONFIG_DIR, "tiers_ui.json")),
    "last_loaded": datetime.utcnow()
}

def reload_tiers():
    TIERS_CACHE["backend"] = load_json(os.path.join(CONFIG_DIR, "tiers.json"))
    TIERS_CACHE["ui"] = load_json(os.path.join(CONFIG_DIR, "tiers_ui.json"))
    TIERS_CACHE["last_loaded"] = datetime.utcnow()
    log("Tier configuration reloaded from disk.")

# ==============================================================
#  TIERS ENDPOINTS
# ==============================================================

@app.get("/tiers", response_class=JSONResponse)
async def get_tiers():
    backend_data = TIERS_CACHE["backend"]
    ui_data = TIERS_CACHE["ui"]

    if not backend_data or not ui_data:
        raise HTTPException(status_code=500, detail="Tier configuration not found or invalid.")

    return {
        "version": backend_data.get("version", "1.0"),
        "tiers_backend": backend_data.get("tiers", []),
        "tiers_ui": ui_data.get("tiers", []),
        "last_loaded": TIERS_CACHE["last_loaded"].isoformat() + "Z"
    }

@app.get("/tiers/version", response_class=JSONResponse)
async def get_tiers_version():
    manifest = load_manifest()
    if manifest:
        return {
            "version": manifest["backend"]["version"],
            "generated_at": manifest["generated_at"],
            "status": manifest["status"],
            "backend_checksum": manifest["backend"]["checksum"],
            "frontend_checksum": manifest["frontend"]["checksum"]
        }

    backend_data = TIERS_CACHE["backend"]
    version = backend_data.get("version", "1.0") if backend_data else "unknown"
    try:
        backend_mtime = os.path.getmtime(os.path.join(CONFIG_DIR, "tiers.json"))
        ui_mtime = os.path.getmtime(os.path.join(CONFIG_DIR, "tiers_ui.json"))
        last_updated = max(backend_mtime, ui_mtime)
    except Exception:
        last_updated = TIERS_CACHE["last_loaded"].timestamp()
    return {
        "version": version,
        "last_updated": datetime.utcfromtimestamp(last_updated).isoformat() + "Z",
        "manifest_found": False
    }

@app.get("/manifest", response_class=JSONResponse)
async def get_manifest():
    manifest = load_manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="tiers_manifest.json not found.")
    return manifest

@app.post("/tiers/reload", response_class=PlainTextResponse)
async def reload_tiers_route():
    reload_tiers()
    return f"Tier configuration reloaded at {TIERS_CACHE['last_loaded'].isoformat()}Z"

# ==============================================================
#  SUPABASE KEEPALIVE + STARTUP
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
        await asyncio.sleep(6 * 60 * 60)

@app.on_event("startup")
async def on_startup():
    check_env_keys()
    asyncio.create_task(keepalive_loop())
    manifest = load_manifest()
    if manifest:
        reload_tiers()
        log(f"Manifest loaded at startup → version {manifest['backend']['version']}")
    log("Exclusivity Backend v6.3 started successfully.")
