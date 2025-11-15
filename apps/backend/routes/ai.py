# =====================================================
# 🎙 Exclusivity Backend — AI & Voice Routes (Merged, Safe)
# =====================================================
# - Preserves existing endpoints: /respond, /voice-test/orion, /voice-test/lyric
# - Adds brand brain: /init-questions, /init-answers (no hard deps)
# - ElevenLabs TTS primary, OpenAI TTS fallback (optional)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import os, base64, requests

# ---------- Optional OpenAI (fallback only) ----------
try:
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
except Exception:
    openai = None  # if not installed or key missing, fallback will error cleanly

router = APIRouter()

# ---------- Env config ----------
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_MODEL   = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
ELEVEN_ORION   = os.getenv("ELEVENLABS_ORION_VOICE")
ELEVEN_LYRIC   = os.getenv("ELEVENLABS_LYRIC_VOICE")
OPENAI_TTS_MODEL = os.getenv("AI_MODEL_TTS", "gpt-4o-mini-tts")
OPENAI_CHAT_MODEL = os.getenv("AI_MODEL_GPT", "gpt-5")

# =====================================================
# Helpers
# =====================================================

def _tts_elevenlabs(text: str, voice_id: str) -> bytes:
    if not ELEVEN_API_KEY or not voice_id:
        raise HTTPException(500, "ElevenLabs not configured (missing key or voice_id)")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
    payload = {"text": text, "model_id": ELEVEN_MODEL,
               "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code != 200:
        raise HTTPException(500, f"ElevenLabs error: {r.text}")
    return r.content

def _tts_openai(text: str, voice: str = "alloy") -> bytes:
    if not openai:
        raise HTTPException(500, "OpenAI TTS not available (package not installed)")
    try:
        # Compatible with OpenAI TTS (Responses API style)
        resp = openai.audio.speech.create(model=OPENAI_TTS_MODEL, voice=voice, input=text)
        return resp.read()
    except Exception as e:
        raise HTTPException(500, f"OpenAI TTS error: {e}")

# =====================================================
# PRESERVED: Basic AI text response
# =====================================================

@router.get("/respond", tags=["ai"])
def ai_respond(prompt: str = "Hello Orion!"):
    """Basic AI text response test using OpenAI chat if available."""
    if not openai:
        # Graceful behavior if OpenAI not installed
        return {"prompt": prompt, "response": "OpenAI not configured; echo: " + prompt}
    try:
        completion = openai.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        answer = completion.choices[0].message.content
        return {"prompt": prompt, "response": answer}
    except Exception as e:
        raise HTTPException(500, str(e))

# =====================================================
# PRESERVED: Voice tests (Orion / Lyric)
# =====================================================

@router.get("/voice-test/orion", tags=["ai"])
def voice_test_orion():
    """Generate test audio using Orion's ElevenLabs voice; fallback to OpenAI."""
    text = "Hello, I am Orion. The Exclusivity platform is online and stable."
    try:
        audio = _tts_elevenlabs(text, ELEVEN_ORION) if (ELEVEN_API_KEY and ELEVEN_ORION) else _tts_openai(text, "alloy")
        return {
            "speaker": "orion",
            "length_bytes": len(audio),
            "audio_base64": base64.b64encode(audio).decode("utf-8")[:80] + "..."
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/voice-test/lyric", tags=["ai"])
def voice_test_lyric():
    """Generate test audio using Lyric's ElevenLabs voice; fallback to OpenAI."""
    text = "Hello, I am Lyric. All systems are active and synchronized."
    try:
        audio = _tts_elevenlabs(text, ELEVEN_LYRIC) if (ELEVEN_API_KEY and ELEVEN_LYRIC) else _tts_openai(text, "verse")
        return {
            "speaker": "lyric",
            "length_bytes": len(audio),
            "audio_base64": base64.b64encode(audio).decode("utf-8")[:80] + "..."
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(500, str(e))

# =====================================================
# NEW: Brand Intelligence endpoints (safe & additive)
# =====================================================

INIT_QUESTIONS: List[str] = [
    "Describe your brand in one sentence.",
    "Who is your ideal customer?",
    "Top 3 brand colors?",
    "Typical order value & margin range?",
    "Any words we should avoid in copy?"
]

@router.get("/init-questions", tags=["ai"])
def init_questions():
    """Return the initial brand questions for Orion/Lyric onboarding."""
    return {"questions": INIT_QUESTIONS}

class InitAnswersIn(BaseModel):
    merchant_id: str
    answers: Dict[str, str]

@router.post("/init-answers", tags=["ai"])
def save_init_answers(inb: InitAnswersIn):
    """
    Stub persistence: echoes what would be saved.
    (Wire to Supabase later by replacing this body with an update call.)
    """
    tone_tags = list(inb.answers.keys())
    return {"ok": True, "merchant_id": inb.merchant_id, "tone_tags": tone_tags}
