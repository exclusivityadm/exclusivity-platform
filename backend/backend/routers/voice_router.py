from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import requests
import io
import os

router = APIRouter(prefix="/voice", tags=["voice"])

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

@router.get("/speak")
def speak(text: str = Query(...), agent: str = Query("orion")):
    """
    Converts text to speech using ElevenLabs.
    Example:
    /voice/speak?text=Hello&agent=orion
    """

    if not ELEVEN_API_KEY:
        raise HTTPException(status_code=500, detail="ElevenLabs API key missing")

    # Assign voice IDs or names for Orion and Lyric
    voices = {
        "orion": "Adam",  # try male voice
        "lyric": "Bella"  # try female voice
    }

    voice_name = voices.get(agent.lower(), "Adam")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_name}"

    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.8}
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"ElevenLabs error: {response.text}")

    return StreamingResponse(io.BytesIO(response.content), media_type="audio/mpeg")
