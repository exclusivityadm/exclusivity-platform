# =====================================================
# 🎙 Exclusivity Backend - AI & Voice Routes
# =====================================================

from fastapi import APIRouter, HTTPException
import os
import base64
import requests
import openai

router = APIRouter()

# -----------------------------------------------------
# 🧠 Configuration
# -----------------------------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")
ELEVEN_ORION = os.getenv("ELEVENLABS_ORION_VOICE")
ELEVEN_LYRIC = os.getenv("ELEVENLABS_LYRIC_VOICE")

# -----------------------------------------------------
# 🧩 Helper: Text-to-Speech (ElevenLabs)
# -----------------------------------------------------
def generate_elevenlabs_audio(text: str, voice_id: str) -> bytes:
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
    r = requests.post(url, json=payload, headers=headers)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=f"ElevenLabs error: {r.text}")
    return r.content

# -----------------------------------------------------
# 🧩 Helper: OpenAI Fallback TTS
# -----------------------------------------------------
def generate_openai_audio(text: str, voice: str = "alloy") -> bytes:
    try:
        response = openai.audio.speech.create(
            model=os.getenv("AI_MODEL_TTS", "gpt-4o-mini-tts"),
            voice=voice,
            input=text
        )
        return response.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI TTS error: {str(e)}")

# -----------------------------------------------------
# 🧠 Route: Text Response (AI Chat Test)
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
# 🎧 Route: Voice Test (Orion)
# -----------------------------------------------------
@router.get("/voice-test/orion", tags=["ai"])
def voice_test_orion():
    """
    Generates test audio using Orion's ElevenLabs voice.
    Falls back to OpenAI if ElevenLabs fails.
    """
    sample_text = "Hello, I am Orion. The Exclusivity platform is online and stable."
    try:
        if ELEVEN_API_KEY and ELEVEN_ORION:
            audio_data = generate_elevenlabs_audio(sample_text, ELEVEN_ORION)
        else:
            audio_data = generate_openai_audio(sample_text, voice="alloy")
        encoded = base64.b64encode(audio_data).decode("utf-8")
        return {"speaker": "orion", "length_bytes": len(audio_data), "audio_base64": encoded[:80] + "..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# 🎧 Route: Voice Test (Lyric)
# -----------------------------------------------------
@router.get("/voice-test/lyric", tags=["ai"])
def voice_test_lyric():
    """
    Generates test audio using Lyric's ElevenLabs voice.
    Falls back to OpenAI if ElevenLabs fails.
    """
    sample_text = "Hello, I am Lyric. All systems are active and synchronized."
    try:
        if ELEVEN_API_KEY and ELEVEN_LYRIC:
            audio_data = generate_elevenlabs_audio(sample_text, ELEVEN_LYRIC)
        else:
            audio_data = generate_openai_audio(sample_text, voice="verse")
        encoded = base64.b64encode(audio_data).decode("utf-8")
        return {"speaker": "lyric", "length_bytes": len(audio_data), "audio_base64": encoded[:80] + "..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
