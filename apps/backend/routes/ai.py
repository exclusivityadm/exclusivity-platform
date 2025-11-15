# =====================================================
# 🎙 Exclusivity Backend — AI & Voice Routes (safe, merged)
# =====================================================
# - Endpoints:
#   GET  /ai/respond?prompt=...
#   GET  /ai/voice-test/orion
#   GET  /ai/voice-test/lyric
#   GET  /ai/init-questions
#   POST /ai/init-answers  { merchant_id, answers: { ... } }
#
# - Import-safe: OpenAI is optional; ElevenLabs via urllib (no 'requests' required).
# - No Supabase dependency; /init-answers echoes what would be saved.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import os, base64, json, urllib.request, urllib.error

router = APIRouter()

# ---------- Config (env) ----------
ELEVEN_API_KEY   = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_MODEL     = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
ELEVEN_ORION     = os.getenv("ELEVENLABS_ORION_VOICE")
ELEVEN_LYRIC     = os.getenv("ELEVENLABS_LYRIC_VOICE")
OPENAI_TTS_MODEL = os.getenv("AI_MODEL_TTS", "gpt-4o-mini-tts")
OPENAI_CHAT_MODEL = os.getenv("AI_MODEL_GPT", "gpt-5")

# Optional OpenAI (guarded)
try:
    # Prefer OpenAI v1 client if available
    from openai import OpenAI  # type: ignore
    _client = OpenAI()
except Exception:
    try:
        # Fallback to legacy import if present
        import openai  # type: ignore
        openai.api_key = os.getenv("OPENAI_API_KEY")
        _client = None  # use legacy calls
    except Exception:
        openai = None
        _client = None

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
# PRESERVED: Basic AI text response
# =====================================================
@router.get("/respond", tags=["ai"])
def ai_respond(prompt: str = "Hello Orion!"):
    """Basic AI text response test."""
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
    # No OpenAI configured -> echo
    return {"prompt": prompt, "response": "OpenAI not configured; echo: " + prompt}

# =====================================================
# PRESERVED: Voice tests (Orion / Lyric)
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
# NEW: Brand Intelligence endpoints
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
    # Echo-only stub (persist to Supabase later if desired)
    tone_tags = list(inb.answers.keys())
    return {"ok": True, "merchant_id": inb.merchant_id, "tone_tags": tone_tags}
