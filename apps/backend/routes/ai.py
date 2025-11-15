# =====================================================
# 🎙 Exclusivity Backend — AI & Voice Routes (with Range streaming)
# =====================================================

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, List, Optional, Tuple
import os, base64, json, urllib.request, urllib.error

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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()

# ---------- ElevenLabs TTS ----------
def _tts_elevenlabs(text: str, voice_id: str) -> bytes:
    if not ELEVEN_API_KEY or not voice_id:
        raise HTTPException(500, "ElevenLabs not configured (missing key or voice_id)")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
    payload = {"text": text, "model_id": ELEVEN_MODEL,
               "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    try:
        return _http_post_json(url, payload, headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise HTTPException(500, f"ElevenLabs {e.code}: {body}")
    except Exception as e:
        raise HTTPException(500, f"ElevenLabs error: {e}")

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
            resp = openai.audio.speech.create(model=OPENAI_TTS_MODEL, voice=voice, input=
