# apps/backend/routes/voice.py
# =====================================================
# /voice compatibility + direct endpoints
# - Handles OPTIONS cleanly (no more 400 preflights)
# - Supports POST /voice (JSON → base64 audio) using your env names
# - Redirects legacy paths to /ai/voice-test/... (which already work)
# - Exposes /voice/orion.stream and /voice/lyric.stream for <audio> tags
# =====================================================

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel
import os, base64, json, urllib.request, urllib.error

router = APIRouter()

# ----- Env (exact names you provided) -----
ELEVEN_API_KEY     = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_MODEL       = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
ELEVEN_VOICE_ORION = os.getenv("ELEVENLABS_VOICE_ORION")
ELEVEN_VOICE_LYRIC = os.getenv("ELEVENLABS_VOICE_LYRIC")

def _http_post_json(url: str, payload: dict, headers: dict, timeout: int = 30) -> bytes:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise HTTPException(500, f"HTTP {e.code} {e.reason}: {body}")
    except Exception as e:
        raise HTTPException(500, f"Request error: {e}")

def _tts_elevenlabs(text: str, voice_id: str) -> bytes:
    if not ELEVEN_API_KEY or not voice_id:
        raise HTTPException(500, "Missing ELEVENLABS_API_KEY or voice id")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": ELEVEN_MODEL,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    return _http_post_json(url, payload, headers)

# ---------- CORS preflight catcher ----------
@router.options("/{path:path}")
def options_any(path: str, request: Request):
    return Response(status_code=200)

# ---------- Helpful root ----------
@router.get("/")
def root():
    return {
        "moved": True,
        "use": {
            "orion_stream": "/ai/voice-test/orion.stream",
            "lyric_stream": "/ai/voice-test/lyric.stream",
            "orion_json": "/ai/voice-test/orion",
            "lyric_json": "/ai/voice-test/lyric",
        }
    }

# ---------- Legacy redirects (keep old callers working) ----------
@router.get("/orion")
def legacy_orion_json():  return RedirectResponse("/ai/voice-test/orion", status_code=307)

@router.get("/lyric")
def legacy_lyric_json():  return RedirectResponse("/ai/voice-test/lyric", status_code=307)

@router.get("/orion.stream")
def legacy_orion_stream():  return RedirectResponse("/ai/voice-test/orion.stream", status_code=307)

@router.get("/lyric.stream")
def legacy_lyric_stream():  return RedirectResponse("/ai/voice-test/lyric.stream", status_code=307)

# ---------- Direct POST /voice (JSON → base64) ----------
class VoiceRequest(BaseModel):
    speaker: str
    text: str

@router.post("/")
def generate_voice(req: VoiceRequest):
    speaker = (req.speaker or "").strip().lower()
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "Text is empty")
    if speaker == "orion":
        vid = ELEVEN_VOICE_ORION
    elif speaker == "lyric":
        vid = ELEVEN_VOICE_LYRIC
    else:
        raise HTTPException(400, f"Invalid speaker: {speaker}")
    audio = _tts_elevenlabs(text, vid)
    return {"speaker": speaker, "length_bytes": len(audio),
            "audio_base64": base64.b64encode(audio).decode()[:80] + "..."}

# ---------- Direct streams at /voice/* (optional convenience) ----------
@router.get("/orion.direct.stream")
def orion_direct_stream():
    audio = _tts_elevenlabs("Hello, I am Orion.", ELEVEN_VOICE_ORION)
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"Accept-Ranges":"bytes","Content-Length":str(len(audio))})

@router.get("/lyric.direct.stream")
def lyric_direct_stream():
    audio = _tts_elevenlabs("Hello, I am Lyric.", ELEVEN_VOICE_LYRIC)
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"Accept-Ranges":"bytes","Content-Length":str(len(audio))})
