# =====================================================
# 🎙 Exclusivity Backend — AI & Voice Routes (with Range streaming)
# =====================================================

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Tuple
import os, base64, json, urllib.request, urllib.error, io

router = APIRouter()

# ---------- Config (env) ----------
ELEVEN_API_KEY    = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_MODEL      = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
ELEVEN_ORION      = os.getenv("ELEVENLABS_ORION_VOICE")
ELEVEN_LYRIC      = os.getenv("ELEVENLABS_LYRIC_VOICE")
OPENAI_TTS_MODEL  = os.getenv("AI_MODEL_TTS", "gpt-4o-mini-tts")
OPENAI_CHAT_MODEL = os.getenv("AI_MODEL_GPT", "gpt-5")

# Optional OpenAI client(s), fully guarded
try:
    from openai import OpenAI  # v1 client
    _client = OpenAI()
except Exception:
    _client = None
    try:
        import openai  # legacy
        openai.api_key = os.getenv("OPENAI_API_KEY")
    except Exception:
        openai = None

# ---------- Minimal HTTP helper (stdlib) ----------
def _http_post_json(url: str, payload: Dict, headers: Dict[str, str], timeout: int = 30) -> bytes:
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

# ---------- ElevenLabs TTS ----------
def _tts_elevenlabs(text: str, voice_id: str) -> bytes:
    if not ELEVEN_API_KEY or not voice_id:
        raise HTTPException(500, "ElevenLabs not configured (missing key or voice_id)")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
    payload = {"text": text, "model_id": ELEVEN_MODEL,
               "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    return _http_post_json(url, payload, headers)

# ---------- OpenAI TTS (optional) ----------
def _tts_openai(text: str, voice: str = "alloy") -> bytes:
    if _client:
        try:
            resp = _client.audio.speech.create(model=OPENAI_TTS_MODEL, voice=voice, input=text)
            return resp.read()
        except Exception as e:
            raise HTTPException(500, f"OpenAI TTS error: {e}")
    if 'openai' in globals() and openai:
        try:
            resp = openai.audio.speech.create(model=OPENAI_TTS_MODEL, voice=voice, input=text)  # type: ignore
            return resp.read()
        except Exception as e:
            raise HTTPException(500, f"OpenAI TTS error: {e}")
    raise HTTPException(500, "OpenAI TTS not available (package/key missing)")

# =====================================================
# Basic AI text response (preserved)
# =====================================================
@router.get("/respond", tags=["ai"])
def ai_respond(prompt: str = "Hello Orion!"):
    if _client:
        try:
            c = _client.chat.completions.create(
                model=OPENAI_CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            return {"prompt": prompt, "response": c.choices[0].message.content}
        except Exception as e:
            raise HTTPException(500, str(e))
    if 'openai' in globals() and openai:
        try:
            c = openai.chat.completions.create(  # type: ignore
                model=OPENAI_CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            return {"prompt": prompt, "response": c.choices[0].message.content}
        except Exception as e:
            raise HTTPException(500, str(e))
    return {"prompt": prompt, "response": "OpenAI not configured; echo: " + prompt}

# =====================================================
# Voice tests — JSON (preserved)
# =====================================================
@router.get("/voice-test/orion", tags=["ai"])
def voice_test_orion():
    text = "Hello, I am Orion. The Exclusivity platform is online and stable."
    audio = _tts_elevenlabs(text, ELEVEN_ORION) if (ELEVEN_API_KEY and ELEVEN_ORION) else _tts_openai(text, "alloy")
    return {"speaker": "orion", "length_bytes": len(audio),
            "audio_base64": base64.b64encode(audio).decode()[:80] + "..."}

@router.get("/voice-test/lyric", tags=["ai"])
def voice_test_lyric():
    text = "Hello, I am Lyric. All systems are active and synchronized."
    audio = _tts_elevenlabs(text, ELEVEN_LYRIC) if (ELEVEN_API_KEY and ELEVEN_LYRIC) else _tts_openai(text, "verse")
    return {"speaker": "lyric", "length_bytes": len(audio),
            "audio_base64": base64.b64encode(audio).decode()[:80] + "..."}

# =====================================================
# Range-aware streaming helpers
# =====================================================
def _parse_range(range_header: Optional[str], total: int) -> Optional[Tuple[int, int]]:
    # Example: "bytes=0-1023"
    if not range_header or not range_header.startswith("bytes="):
        return None
    try:
        rng = range_header.split("=", 1)[1]
        start_str, end_str = (rng.split("-", 1) + [""])[:2]
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else total - 1
        if start < 0 or end < start or end >= total:
            return None
        return (start, end)
    except Exception:
        return None

def _stream_bytes(buf: bytes, start: int, end: int, media_type: str = "audio/mpeg") -> Response:
    chunk = memoryview(buf)[start:end+1]
    headers = {
        "Content-Range": f"bytes {start}-{end}/{len(buf)}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(len(chunk)),
    }
    return Response(content=chunk.tobytes(), status_code=206, media_type=media_type, headers=headers)

def _full_bytes(buf: bytes, media_type: str = "audio/mpeg") -> Response:
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(len(buf)),
    }
    return Response(content=buf, media_type=media_type, headers=headers)

# =====================================================
# Voice tests — STREAM (range-aware; recommended for frontend)
# =====================================================
@router.get("/voice-test/orion.stream", tags=["ai"])
def voice_test_orion_stream(request: Request):
    text = "Hello, I am Orion. The Exclusivity platform is online and stable."
    audio = _tts_elevenlabs(text, ELEVEN_ORION) if (ELEVEN_API_KEY and ELEVEN_ORION) else _tts_openai(text, "alloy")
    rng = _parse_range(request.headers.get("range"), len(audio))
    if rng:
        return _stream_bytes(audio, *rng)
    return _full_bytes(audio)

@router.get("/voice-test/lyric.stream", tags=["ai"])
def voice_test_lyric_stream(request: Request):
    text = "Hello, I am Lyric. All systems are active and synchronized."
    audio = _tts_elevenlabs(text, ELEVEN_LYRIC) if (ELEVEN_API_KEY and ELEVEN_LYRIC) else _tts_openai(text, "verse")
    rng = _parse_range(request.headers.get("range"), len(audio))
    if rng:
        return _stream_bytes(audio, *rng)
    return _full_bytes(audio)

# =====================================================
# Brand Intelligence (safe)
# =====================================================
INIT_QUESTIONS: List[str] = [
    "Describe your brand in one sentence.",
    "Who is your ideal customer?",
    "Top 3 brand colors?",
    "Typical order value & margin range?",
    "Any words we should avoid in copy?",
]

@router.get("/init-questions", tags=["ai"])
def init_questions():
    return {"questions": INIT_QUESTIONS}

class InitAnswersIn(BaseModel):
    merchant_id: str
    answers: Dict[str, str]

@router.post("/init-answers", tags=["ai"])
def save_init_answers(inb: InitAnswersIn):
    tone_tags = list(inb.answers.keys())
    return {"ok": True, "merchant_id": inb.merchant_id, "tone_tags": tone_tags}
