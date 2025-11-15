# =====================================================
# /voice router (no redirects on POST; CORS-safe)
# - OPTIONS preflight: 200
# - POST /voice and /voice/ (both) -> JSON {audio_base64}
# - Legacy redirects for /voice/*.stream to /ai/voice-test/*.stream
# =====================================================

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel
import os, base64, json, urllib.request, urllib.error

router = APIRouter()

# ----- Env (exact names) -----
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

# ---------- CORS preflight ----------
@router.options("/{path:path}")
def options_any(path: str, request: Request):
    return Response(status_code=200)

# ---------- Helpful root ----------
@router.get("/")
def root():
    return {
        "moved": False,
        "direct_stream": {
            "orion": "/ai/voice-test/orion.stream",
            "lyric": "/ai/voice-test/lyric.stream",
        },
        "json_post": "/voice or /voice/  (body: {speaker:'orion'|'lyric', text:'...'})",
    }

# ---------- Legacy redirects for *.stream ----------
@router.get("/orion.stream")
def legacy_orion_stream():  return RedirectResponse("/ai/voice-test/orion.stream", status_code=307)

@router.get("/lyric.stream")
def legacy_lyric_stream():  return RedirectResponse("/ai/voice-test/lyric.stream", status_code=307)

# ---------- JSON POST: accept both /voice and /voice/ ----------
class VoiceRequest(BaseModel):
    speaker: str
    text: str

def _gen_voice_response(speaker: str, text: str):
    s = (speaker or "").strip().lower()
    if not text.strip():
        raise HTTPException(400, "Text is empty")
    if s == "orion":
        vid = ELEVEN_VOICE_ORION
    elif s == "lyric":
        vid = ELEVEN_VOICE_LYRIC
    else:
        raise HTTPException(400, f"Invalid speaker: {speaker}")
    audio = _tts_elevenlabs(text, vid)
    return {
        "speaker": s,
        "length_bytes": len(audio),
        "audio_base64": base64.b64encode(audio).decode()
    }

@router.post("", include_in_schema=False)
def post_voice_no_slash(req: VoiceRequest):
    return _gen_voice_response(req.speaker, req.text)

@router.post("/")
def post_voice_with_slash(req: VoiceRequest):
    return _gen_voice_response(req.speaker, req.text)
