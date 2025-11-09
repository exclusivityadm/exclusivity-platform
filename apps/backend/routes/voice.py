from fastapi import APIRouter, Response
from pydantic import BaseModel
from openai import OpenAI
import base64
import os

router = APIRouter()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define request body model
class VoiceRequest(BaseModel):
    text: str

# --- Orion Voice ---
@router.post("/orion")
async def play_orion(request: VoiceRequest):
    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",  # Orion’s voice ID
            input=request.text
        )
        audio_data = speech.read()
        b64_audio = base64.b64encode(audio_data).decode("utf-8")
        return {"audio": b64_audio}
    except Exception as e:
        return {"error": str(e)}

# --- Lyric Voice ---
@router.post("/lyric")
async def play_lyric(request: VoiceRequest):
    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="verse",  # Lyric’s voice ID
            input=request.text
        )
        audio_data = speech.read()
        b64_audio = base64.b64encode(audio_data).decode("utf-8")
        return {"audio": b64_audio}
    except Exception as e:
        return {"error": str(e)}

# --- Health Check ---
@router.get("/")
async def voice_root():
    return {"status": "ok", "message": "Voice routes active"}
