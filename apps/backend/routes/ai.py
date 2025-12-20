# apps/backend/routes/ai.py
# =====================================================
# Exclusivity Backend — AI Routes (Canonical)
#
# Preserved endpoints:
#   GET  /ai/respond?prompt=...
#   POST /ai/chat                 -> {persona, message}
#   GET  /ai/voice-test/orion
#   GET  /ai/voice-test/lyric
#   GET  /ai/voice-test/orion.stream
#   GET  /ai/voice-test/lyric.stream
#   GET  /ai/init-questions
#   POST /ai/init-answers
#   GET  /ai/env-report
#
# Added endpoints (final product utility layer):
#   GET  /ai/daily-briefing?merchant_id=...&persona=orion|lyric
#   POST /ai/action/preview        -> preview mode (no execution)
#   POST /ai/action/execute        -> tier-gated execution (paid tiers)
#
# Env keys:
#   ELEVENLABS_API_KEY (optional, enables ElevenLabs TTS)
#   ELEVENLABS_MODEL=eleven_multilingual_v2 (optional)
#   ELEVENLABS_VOICE_ORION (optional)
#   ELEVENLABS_VOICE_LYRIC (optional)
#   OPENAI_API_KEY (optional, enables OpenAI chat + TTS fallback)
#   AI_MODEL_TTS=gpt-4o-mini-tts (optional)
#   AI_MODEL_GPT=gpt-5.1 (optional)
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Tuple
import os, base64, json, urllib.request, urllib.error

router = APIRouter(tags=["ai"])  # prefix owned by main.py

# ---------- Config (env) ----------
ELEVEN_API_KEY     = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_MODEL       = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
ELEVEN_VOICE_ORION = os.getenv("ELEVENLABS_VOICE_ORION")
ELEVEN_VOICE_LYRIC = os.getenv("ELEVENLABS_VOICE_LYRIC")

OPENAI_KEY         = os.getenv("OPENAI_API_KEY")
OPENAI_TTS_MODEL   = os.getenv("AI_MODEL_TTS", "gpt-4o-mini-tts")
OPENAI_CHAT_MODEL  = os.getenv("AI_MODEL_GPT", "gpt-5.1")

# ---------- Optional: hardened chat (preferred if present) ----------
_hardened_chat = None
try:
    from apps.backend.services.ai.hardening import chat as _hc  # type: ignore
    _hardened_chat = _hc
except Exception:
    _hardened_chat = None

# ---------- Optional OpenAI client(s), fully guarded ----------
_client = None
openai_legacy = None
try:
    from openai import OpenAI  # v1 client
    _client = OpenAI()
except Exception:
    _client = None
    try:
        import openai as openai_legacy  # type: ignore
        if OPENAI_KEY:
            openai_legacy.api_key = OPENAI_KEY
    except Exception:
        openai_legacy = None

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
        raise HTTPException(500, "ElevenLabs not configured (missing ELEVENLABS_API_KEY or voice id)")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": ELEVEN_MODEL,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    return _http_post_json(url, payload, headers)

# ---------- OpenAI TTS (optional) ----------
def _tts_openai(text: str, voice: str = "alloy") -> bytes:
    if _client:
        try:
            resp = _client.audio.speech.create(model=OPENAI_TTS_MODEL, voice=voice, input=text)
            return resp.read()
        except Exception as e:
            raise HTTPException(500, f"OpenAI TTS error: {e}")
    if openai_legacy:
        try:
            resp = openai_legacy.audio.speech.create(model=OPENAI_TTS_MODEL, voice=voice, input=text)  # type: ignore
            return resp.read()
        except Exception as e:
            raise HTTPException(500, f"OpenAI TTS error: {e}")
    raise HTTPException(500, "OpenAI TTS not available (package/key missing)")

# ---------- Chat helper ----------
def _chat(persona: str, message: str) -> Dict[str, object]:
    """
    Canonical chat wrapper.
    - Uses hardening module if available.
    - Otherwise uses OpenAI client if configured.
    - Otherwise returns safe echo.
    """
    persona = (persona or "orion").lower().strip()
    if persona not in ["orion", "lyric"]:
        persona = "orion"

    if _hardened_chat:
        try:
            res = _hardened_chat(persona=persona, message=message)
            # Expect res: {ok, reply, message, status_code, ...}
            if isinstance(res, dict):
                return res
        except Exception:
            pass

    # fallback to OpenAI
    if _client:
        try:
            c = _client.chat.completions.create(
                model=OPENAI_CHAT_MODEL,
                messages=[{"role": "user", "content": message}],
            )
            reply = c.choices[0].message.content
            return {"ok": True, "persona": persona, "reply": reply, "mode": "openai_v1"}
        except Exception as e:
            return {"ok": False, "persona": persona, "message": f"Chat error: {e}", "status_code": 500}

    if openai_legacy:
        try:
            c = openai_legacy.chat.completions.create(  # type: ignore
                model=OPENAI_CHAT_MODEL,
                messages=[{"role": "user", "content": message}],
            )
            reply = c.choices[0].message.content
            return {"ok": True, "persona": persona, "reply": reply, "mode": "openai_legacy"}
        except Exception as e:
            return {"ok": False, "persona": persona, "message": f"Chat error: {e}", "status_code": 500}

    return {"ok": True, "persona": persona, "reply": "OpenAI not configured; echo: " + message, "mode": "echo"}

# =====================================================
# Basic AI text response (preserved)
# =====================================================
@router.get("/respond")
def ai_respond(prompt: str = "Hello Orion!"):
    res = _chat(persona="orion", message=prompt)
    if res.get("ok"):
        return {"prompt": prompt, "response": res.get("reply")}
    return {"prompt": prompt, "response": res.get("message")}

class ChatIn(BaseModel):
    persona: str = "orion"  # "orion" | "lyric"
    message: str

@router.post("/chat")
async def ai_chat(inb: ChatIn):
    res = _chat(persona=inb.persona, message=inb.message)
    if res.get("ok"):
        return JSONResponse(content=res, status_code=200)
    return JSONResponse(content=res, status_code=int(res.get("status_code") or 500))

# =====================================================
# Voice tests — JSON (base64 sample) (preserved)
# =====================================================
@router.get("/voice-test/orion")
def voice_test_orion():
    text = "Hello, I am Orion. The Exclusivity platform is online and stable."
    audio = _tts_elevenlabs(text, ELEVEN_VOICE_ORION) if ELEVEN_VOICE_ORION else _tts_openai(text, "alloy")
    return {"speaker": "orion", "length_bytes": len(audio),
            "audio_base64": base64.b64encode(audio).decode()[:80] + "..."}

@router.get("/voice-test/lyric")
def voice_test_lyric():
    text = "Hello, I am Lyric. All systems are active and synchronized."
    audio = _tts_elevenlabs(text, ELEVEN_VOICE_LYRIC) if ELEVEN_VOICE_LYRIC else _tts_openai(text, "verse")
    return {"speaker": "lyric", "length_bytes": len(audio),
            "audio_base64": base64.b64encode(audio).decode()[:80] + "..."}

# =====================================================
# Range-aware streaming helpers (preserved)
# =====================================================
def _parse_range(range_header: Optional[str], total: int) -> Optional[Tuple[int, int]]:
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
    headers = {"Accept-Ranges": "bytes", "Content-Length": str(len(buf))}
    return Response(content=buf, media_type=media_type, headers=headers)

# =====================================================
# Voice tests — STREAM (preserved)
# =====================================================
@router.get("/voice-test/orion.stream")
def voice_test_orion_stream(request: Request):
    text = "Hello, I am Orion. The Exclusivity platform is online and stable."
    audio = _tts_elevenlabs(text, ELEVEN_VOICE_ORION) if ELEVEN_VOICE_ORION else _tts_openai(text, "alloy")
    rng = _parse_range(request.headers.get("range"), len(audio))
    if rng:
        return _stream_bytes(audio, *rng)
    return _full_bytes(audio)

@router.get("/voice-test/lyric.stream")
def voice_test_lyric_stream(request: Request):
    text = "Hello, I am Lyric. All systems are active and synchronized."
    audio = _tts_elevenlabs(text, ELEVEN_VOICE_LYRIC) if ELEVEN_VOICE_LYRIC else _tts_openai(text, "verse")
    rng = _parse_range(request.headers.get("range"), len(audio))
    if rng:
        return _stream_bytes(audio, *rng)
    return _full_bytes(audio)

# =====================================================
# Brand Intelligence init Q/A (preserved)
# =====================================================
INIT_QUESTIONS: List[str] = [
    "Describe your brand in one sentence.",
    "Who is your ideal customer?",
    "Top 3 brand colors?",
    "Typical order value & margin range?",
    "Any words we should avoid in copy?",
]

@router.get("/init-questions")
def init_questions():
    return {"questions": INIT_QUESTIONS}

class InitAnswersIn(BaseModel):
    merchant_id: str
    answers: Dict[str, str]

@router.post("/init-answers")
def save_init_answers(inb: InitAnswersIn):
    # Persisting answers can be added later; keep stable response shape now
    tone_tags = list(inb.answers.keys())
    return {"ok": True, "merchant_id": inb.merchant_id, "tone_tags": tone_tags}

# =====================================================
# Env report (masked) (preserved)
# =====================================================
def _mask(s: Optional[str], show: int = 4) -> Optional[str]:
    if not s:
        return None
    if len(s) <= show:
        return "*" * len(s)
    return "*" * (len(s) - show) + s[-show:]

@router.get("/env-report")
def env_report():
    return {
        "elevenlabs": {
            "api_key_present": bool(ELEVEN_API_KEY),
            "model": ELEVEN_MODEL,
            "voice_orion_env_present": bool(ELEVEN_VOICE_ORION),
            "voice_lyric_env_present": bool(ELEVEN_VOICE_LYRIC),
        },
        "openai": {
            "api_key_present": bool(OPENAI_KEY),
            "api_key_tail": _mask(OPENAI_KEY),
            "chat_model": OPENAI_CHAT_MODEL,
            "tts_model": OPENAI_TTS_MODEL,
            "client_mode": "v1" if _client else ("legacy" if openai_legacy else "none"),
        },
        "hardening": {"enabled": bool(_hardened_chat)},
    }

# =====================================================
# Daily utility — Daily Briefing (NEW)
# =====================================================
@router.get("/daily-briefing")
async def daily_briefing(merchant_id: str, persona: str = "orion"):
    try:
        from apps.backend.services.daily_briefing import build_daily_briefing  # type: ignore
        res = build_daily_briefing(merchant_id=merchant_id, persona=persona)
        if not res.get("ok"):
            raise HTTPException(500, res.get("error") or "Failed to build briefing")
        return JSONResponse(content=res, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Daily briefing service not available: {e}")

# =====================================================
# Daily utility — Action preview/execute (NEW)
# =====================================================
class ActionIn(BaseModel):
    merchant_id: str
    action: Dict[str, object]

@router.post("/action/preview")
async def action_preview(payload: ActionIn):
    try:
        from apps.backend.services.action_router import preview_action  # type: ignore
        return JSONResponse(content=preview_action(payload.action), status_code=200)
    except Exception as e:
        raise HTTPException(500, f"Action router not available: {e}")

@router.post("/action/execute")
async def action_execute(payload: ActionIn):
    try:
        from apps.backend.services.monetize.entitlements import get_plan_for_merchant, can_execute_actions  # type: ignore
        plan = get_plan_for_merchant(payload.merchant_id)
        if not can_execute_actions(plan):
            return JSONResponse(
                content={
                    "ok": False,
                    "status_code": 403,
                    "plan": plan,
                    "message": "Preview tier cannot execute actions. Upgrade to enable execution.",
                },
                status_code=403,
            )

        from apps.backend.services.action_router import execute_action  # type: ignore
        return JSONResponse(content=execute_action(payload.action), status_code=200)
    except Exception as e:
        raise HTTPException(500, f"Execution surface not available: {e}")
