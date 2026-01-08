# apps/backend/routes/ai.py
# =====================================================
# Exclusivity Backend — AI Routes (Canonical)
#
# LOCKED RULES:
# - Preview is FREE, advisory only, no execution
# - Paid tiers can execute, tier-gated
# - ALL actions are ledgered (preview + execute + denied)
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

# ---------- Optional: hardened chat ----------
_hardened_chat = None
try:
    from apps.backend.services.ai.hardening import chat as _hc  # type: ignore
    _hardened_chat = _hc
except Exception:
    _hardened_chat = None

# ---------- OpenAI clients ----------
_client = None
openai_legacy = None
try:
    from openai import OpenAI
    _client = OpenAI()
except Exception:
    try:
        import openai as openai_legacy  # type: ignore
        if OPENAI_KEY:
            openai_legacy.api_key = OPENAI_KEY
    except Exception:
        pass

# ---------- HTTP helper ----------
def _http_post_json(url: str, payload: Dict, headers: Dict[str, str], timeout: int = 30) -> bytes:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        raise HTTPException(500, f"HTTP request error: {e}")

# ---------- Chat ----------
def _chat(persona: str, message: str) -> Dict[str, object]:
    persona = (persona or "orion").lower().strip()
    if persona not in ("orion", "lyric"):
        persona = "orion"

    if _hardened_chat:
        try:
            return _hardened_chat(persona=persona, message=message)
        except Exception:
            pass

    if _client:
        try:
            c = _client.chat.completions.create(
                model=OPENAI_CHAT_MODEL,
                messages=[{"role": "user", "content": message}],
            )
            return {"ok": True, "persona": persona, "reply": c.choices[0].message.content}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    return {"ok": True, "persona": persona, "reply": "OpenAI not configured; echo: " + message}

# =====================================================
# Core endpoints
# =====================================================

@router.get("/respond")
def ai_respond(prompt: str):
    res = _chat("orion", prompt)
    return {"prompt": prompt, "response": res.get("reply")}

class ChatIn(BaseModel):
    persona: str = "orion"
    message: str

@router.post("/chat")
async def ai_chat(inb: ChatIn):
    return JSONResponse(content=_chat(inb.persona, inb.message), status_code=200)

# =====================================================
# Action execution surface (FINAL)
# =====================================================

class ActionIn(BaseModel):
    merchant_id: str
    persona: Optional[str] = "orion"
    action: Dict[str, object]

@router.post("/action/preview")
async def action_preview(payload: ActionIn):
    try:
        from apps.backend.services.action_router import preview_action
        return JSONResponse(
            content=preview_action(
                payload.action,
                merchant_id=payload.merchant_id,
                persona=payload.persona or "orion",
            ),
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(500, f"Preview failed: {e}")

@router.post("/action/execute")
async def action_execute(payload: ActionIn):
    try:
        from apps.backend.services.action_router import execute_action
        return JSONResponse(
            content=execute_action(
                payload.action,
                merchant_id=payload.merchant_id,
                persona=payload.persona or "orion",
            ),
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {e}")
