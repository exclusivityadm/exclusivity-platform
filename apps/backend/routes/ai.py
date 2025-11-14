# =====================================================
# 🎙 Exclusivity Backend - AI & Voice Routes (Merged)
# =====================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import base64
import requests
import openai
from typing import Dict, Any, Optional, List

# Optional: Supabase client for saving brand intel (init-answers).
# If env vars are missing, endpoints will return a friendly error.
try:
    from supabase import create_client, Client
except Exception:  # pragma: no cover
    create_client = None
    Client = Any  # type: ignore

router = APIRouter()

# -----------------------------------------------------
# 🧠 Configuration (PRESERVED)
# -----------------------------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
ELEVEN_ORION = os.getenv("ELEVENLABS_ORION_VOICE")
ELEVEN_LYRIC = os.getenv("ELEVENLABS_LYRIC_VOICE")

# -----------------------------------------------------
# 🔌 Supabase helper (for init-answers)
# -----------------------------------------------------
def get_supabase_client() -> "Client":
    if create_client is None:
        raise RuntimeError("Supabase client library not installed")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL / key in environment")
    return create_client(url, key)

# -----------------------------------------------------
# 🧩 Helper: Text-to-Speech (ElevenLabs)  (PRESERVED)
# -----------------------------------------------------
def generate_elevenlabs_audio(text: str, voice_id: str) -> bytes:
    if not ELEVEN_API_KEY or not voice_id:
        raise HTTPException(status_code=500, detail="ElevenLabs not configured (missing key or voice_id)")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": ELEVEN_MODEL,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"ElevenLabs error: {r.text}")
    return r.content

# -----------------------------------------------------
# 🧩 Helper: OpenAI Fallback TTS  (PRESERVED)
# -----------------------------------------------------
def generate_openai_audio(text: str, voice: str = "alloy") -> bytes:
    try:
        # Using Responses API style compatible with current setup
        response = openai.audio.speech.create(
            model=os.getenv("AI_MODEL_TTS", "gpt-4o-mini-tts"),
            voice=voice,
            input=text
        )
        return response.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI TTS error: {str(e)}")

# -----------------------------------------------------
# 🧠 Route: Text Response (AI Chat Test)  (PRESERVED)
# GET /ai/respond?prompt=...
# -----------------------------------------------------
@router.get("/respond", tags=["ai"])
def ai_respond(prompt: str = "Hello Orion!"):
    """
    Basic AI text response test using OpenAI.
    """
    try:
        completion = openai.chat.completions.create(
            model=os.getenv("AI_MODEL_GPT", "gpt-5"),
            messages=[{"role": "user", "content": prompt}]
        )
        answer = completion.choices[0].message.content
        return {"prompt": prompt, "response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# 🎧 Route: Voice Test (Orion)  (PRESERVED)
# GET /ai/voice-test/orion
# -----------------------------------------------------
@router.get("/voice-test/orion", tags=["ai"])
def voice_test_orion():
    """
    Generates test audio using Orion's ElevenLabs voice.
    Falls back to OpenAI if ElevenLabs fails or is not configured.
    """
    sample_text = "Hello, I am Orion. The Exclusivity platform is online_
