from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from openai import OpenAI
from ..config import env
from io import BytesIO

router = APIRouter()
client = OpenAI(api_key=env("OPENAI_API_KEY"))

def pick_voice(agent: str | None) -> str:
    if not agent: return env("AI_VOICE_ORION","alloy")
    a = agent.lower()
    if a == "lyric":
        return env("AI_VOICE_LYRIC","verse")
    return env("AI_VOICE_ORION","alloy")

@router.get("/speak")
def speak(
    text: str = Query(..., description="Text to synthesize"),
    agent: str | None = Query(None, description="orion | lyric"),
    voice: str | None = Query(None, description="Override default voice")
):
    try:
        model = env("AI_MODEL_TTS", "gpt-4o-mini-tts")
        chosen_voice = voice or pick_voice(agent)
        with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=chosen_voice,
            input=text,
            format="mp3"
        ) as resp:
            audio_bytes = resp.read()
        bio = BytesIO(audio_bytes)
        bio.seek(0)
        return StreamingResponse(bio, media_type="audio/mpeg",
                                 headers={"Content-Disposition":"inline; filename=speech.mp3"})
    except TypeError:
        try:
            with client.audio.speech.with_streaming_response.create(
                model=model,
                voice=chosen_voice,
                input=text
            ) as resp:
                audio_bytes = resp.read()
            bio = BytesIO(audio_bytes)
            bio.seek(0)
            return StreamingResponse(bio, media_type="audio/mpeg",
                                     headers={"Content-Disposition":"inline; filename=speech.mp3"})
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"TTS generation failed (fallback): {e2}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")
