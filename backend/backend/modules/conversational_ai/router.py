from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from .elevenlabs_voice import synthesize_voice
from .openai_fallback import tts_fallback
from ...config import settings

router = APIRouter()

class SpeakPayload(BaseModel):
    speaker: str  # "orion" | "lyric"
    text: str

@router.post("/speak")
async def speak(payload: SpeakPayload):
    voice_pref = settings.ELEVENLABS_ORION_VOICE if payload.speaker.lower() == "orion" else settings.ELEVENLABS_LYRIC_VOICE
    audio: bytes
    try:
        audio = await synthesize_voice(text=payload.text, voice_pref=voice_pref)
    except Exception:
        try:
            # pick a fallback voice per speaker
            fallback_voice = "alloy" if payload.speaker.lower() == "orion" else "verse"
            audio = await tts_fallback(payload.text, voice=fallback_voice)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS failed: {e}")
    return Response(content=audio, media_type="audio/mpeg")

class ChatPayload(BaseModel):
    speaker: str
    message: str
    history: list[dict] | None = None

@router.post("/chat")
async def chat(payload: ChatPayload):
    speaker_name = "Orion" if payload.speaker.lower() == "orion" else "Lyric"
    text = f"{speaker_name}: I hear you. You said: '{payload.message}'"
    return {"speaker": speaker_name, "text": text}
