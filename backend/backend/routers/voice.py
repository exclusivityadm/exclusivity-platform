import io
import base64
import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import openai

router = APIRouter()

# --- ElevenLabs & OpenAI Config ---
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# --- Default Voices ---
VOICE_PROFILES = {
    "orion": {"provider": "elevenlabs", "voice_id": "vDchjyOZZytffNeZXfZK"},   # male
    "lyric": {"provider": "elevenlabs", "voice_id": "TPbSfDVirzpiSkim8gMw"}  # female
}

# --- Request schema ---
class TTSRequest(BaseModel):
    character: str
    text: str


# === ElevenLabs TTS ===
def elevenlabs_tts(voice_id: str, text: str):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    payload = {"text": text, "model_id": "eleven_turbo_v2"}

    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"ElevenLabs error: {resp.text}")

    return io.BytesIO(resp.content)


# === OpenAI Fallback ===
def openai_tts_fallback(text: str, voice: str):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    with client.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text
    ) as response:
        buf = io.BytesIO(response.read())
        buf.seek(0)
        return buf


# === Primary Route ===
@router.post("/tts")
async def tts(request: TTSRequest):
    char = request.character.lower()
    text = request.text

    if char not in VOICE_PROFILES:
        raise HTTPException(status_code=404, detail=f"Unknown character: {char}")

    profile = VOICE_PROFILES[char]
    try:
        if profile["provider"] == "elevenlabs" and ELEVEN_API_KEY:
            audio_stream = elevenlabs_tts(profile["voice_id"], text)
        else:
            audio_stream = openai_tts_fallback(text, "alloy" if char == "orion" else "verse")

    except Exception as e:
        # fallback if ElevenLabs or OpenAI errors out
        audio_stream = openai_tts_fallback(text, "alloy" if char == "orion" else "verse")

    return StreamingResponse(audio_stream, media_type="audio/mpeg")


# === Legacy Support: /voice/speak ===
@router.get("/speak")
async def legacy_speak(text: str, agent: str = "orion"):
    """
    Legacy route: /voice/speak?text=Hello&agent=orion
    Redirects to new POST /voice/tts endpoint.
    """
    req = TTSRequest(character=agent, text=text)
    return await tts(req)


# === Health Check ===
@router.get("/health")
async def health_check():
    return {"status": "ok", "provider": "ElevenLabs/OpenAI hybrid"}
