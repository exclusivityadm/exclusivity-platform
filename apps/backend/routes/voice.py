# apps/backend/routes/voice.py
# =====================================================
# /voice router (CORS-safe, JSON base64 response)
# - OPTIONS preflight: 200
# - POST /voice and /voice/ -> JSON { speaker, text, audio_base64 }
# - Legacy redirects for /voice/*.stream -> /ai/voice-test/*.stream
# =====================================================

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel
import os
import base64
import requests
import openai

router = APIRouter()

# -------- Environment variables required --------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
ELEVEN_VOICE_ORION = os.getenv("ELEVENLABS_VOICE_ORION")
ELEVEN_VOICE_LYRIC = os.getenv("ELEVENLABS_VOICE_LYRIC")

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY


# -------- Request model --------
class VoiceRequest(BaseModel):
    speaker: str | None = "orion"
    text: str | None = None


# -------- Helpers --------
def _generate_dynamic_text(speaker: str) -> str:
    """
    Use OpenAI to generate a short, spoken-style line for Orion or Lyric.
    """
    if not OPENAI_API_KEY:
        # Fallback if OpenAI is not configured
        if speaker.lower() == "lyric":
            return "Lyric ready and voice link confirmed."
        return "Orion online, Exclusivity system synchronized."

    style = (
        "confident, calm, strategic, like a seasoned advisor"
        if speaker.lower() == "orion"
        else "warm, elegant, intuitive, lightly playful"
    )

    prompt = f"""
    You are {speaker.capitalize()}, one of the twin AI copilots in the Exclusivity system.
    Speak naturally as if greeting a human.
    Output ONLY the final line you would speak. No explanations.

    Voice personality guidelines:
    - Tone style: {style}
    - Keep it short (1–3 sentences)
    - Sound like real spoken language, not a chat message
    - You may reference Exclusivity, systems, or the user, but keep it natural
    - Generate something different every request
    """

    completion = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": prompt}],
    )

    return completion.choices[0].message.content.strip()


def _tts_elevenlabs(text: str, voice_id: str) -> bytes:
    """
    Call ElevenLabs TTS and return raw audio bytes (mp3).
    """
    if not ELEVEN_API_KEY or not voice_id:
        raise HTTPException(status_code=500, detail="Missing ElevenLabs API key or voice ID.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": ELEVEN_MODEL,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.8,
        },
    }

    try:
        resp = requests.post(url, json=payload, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling ElevenLabs: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"ElevenLabs error: {resp.text}")

    return resp.content


def _build_voice_response(speaker: str | None, explicit_text: str | None):
    s = (speaker or "orion").lower()

    if s == "orion":
        voice_id = ELEVEN_VOICE_ORION
    elif s == "lyric":
        voice_id = ELEVEN_VOICE_LYRIC
    else:
        raise HTTPException(status_code=400, detail=f"Invalid speaker: {speaker}")

    text = explicit_text or _generate_dynamic_text(s)
    audio_bytes = _tts_elevenlabs(text, voice_id)

    return {
        "speaker": s,
        "text": text,
        "length_bytes": len(audio_bytes),
        "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
    }


# -------- CORS preflight --------
@router.options("/{path:path}")
async def options_any(path: str, request: Request):
    # FastAPI CORS middleware will add headers; we just need 200
    return Response(status_code=200)


# -------- Main JSON endpoints --------
@router.post("", include_in_schema=False)
def post_voice_no_slash(req: VoiceRequest):
    """
    POST /voice  -> JSON { speaker, text, audio_base64 }
    """
    return _build_voice_response(req.speaker, req.text)


@router.post("/")
def post_voice_with_slash(req: VoiceRequest):
    """
    POST /voice/  -> JSON { speaker, text, audio_base64 }
    """
    return _build_voice_response(req.speaker, req.text)


# -------- Legacy redirect handler for *.stream --------
@router.get("/{name}.stream", include_in_schema=False)
def legacy_stream_redirect(name: str):
    """
    Legacy GET /voice/*.stream -> redirect to /ai/voice-test/*.stream
    so any old links keep working.
    """
    target = f"/ai/voice-test/{name}.stream"
    return RedirectResponse(url=target, status_code=307)


# -------- Simple health/info --------
@router.get("/")
def voice_root():
    return {
        "voice": "online",
        "dynamic_text": bool(OPENAI_API_KEY),
        "elevenlabs": bool(ELEVEN_API_KEY),
    }
