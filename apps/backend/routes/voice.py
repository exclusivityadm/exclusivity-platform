# apps/backend/routes/voice.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import os
import httpx
import base64

router = APIRouter()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ORION_VOICE_ID     = os.getenv("ORION_VOICE_ID")
LYRIC_VOICE_ID     = os.getenv("LYRIC_VOICE_ID")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")  # optional: auto-generate text

class VoiceRequest(BaseModel):
    speaker: str
    text: str | None = None  # if None or "auto", we can generate a line with GPT

async def _maybe_generate_text_with_gpt(speaker: str) -> str:
    """
    Best-effort: if OPENAI_API_KEY is present and no text supplied,
    generate a short intro line. If not available, return a static fallback.
    """
    base_fallback = (
        "Hello, this is Orion — your Exclusivity copilot online and ready."
        if speaker.lower() == "orion"
        else "Hi there, Lyric here — Exclusivity systems confirmed and synchronized."
    )
    if not OPENAI_API_KEY:
        return base_fallback

    try:
        # Lightweight client-free call using httpx to OpenAI Chat Completions
        # Model name may vary; using a generic, widely-available instruct model id.
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Write a single friendly, concise sentence for a voice assistant."},
                {"role": "user", "content": f"Speaker is {speaker}. Keep it <15 words, clear, positive."}
            ],
            "max_tokens": 40,
            "temperature": 0.7
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        if r.status_code == 200:
            j = r.json()
            txt = j["choices"][0]["message"]["content"].strip()
            return txt or base_fallback
    except Exception:
        pass
    return base_fallback

async def _elevenlabs_base(text: str, voice_id: str, as_stream: bool):
    """
    ElevenLabs request:
      - If as_stream=True, hit `/stream` and return StreamingResponse.
      - If as_stream=False, request raw audio and return base64 in JSON.
    """
    if not ELEVENLABS_API_KEY:
        return JSONResponse({"error": "Missing ElevenLabs API key"}, status_code=500)
    if not voice_id:
        return JSONResponse({"error": "Missing voice_id for requested speaker"}, status_code=400)

    base_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            if as_stream:
                # Stream from ElevenLabs and pipe back to client
                stream_url = f"{base_url}/stream"
                # IMPORTANT: Accept audio/mpeg to ensure audio bytes
                headers_stream = headers | {"Accept": "audio/mpeg"}
                upstream = await client.post(stream_url, headers=headers_stream, json=payload)
                if upstream.status_code != 200:
                    return JSONResponse(
                        {"error": "Voice generation failed", "details": upstream.text, "status_code": upstream.status_code},
                        status_code=500,
                    )

                async def _gen():
                    async for chunk in upstream.aiter_bytes():
                        if chunk:
                            yield chunk

                return StreamingResponse(_gen(), media_type="audio/mpeg")

            else:
                # Get the full audio bytes in one shot and return base64
                headers_bytes = headers | {"Accept": "audio/mpeg"}
                r = await client.post(base_url, headers=headers_bytes, json=payload)
                if r.status_code != 200:
                    return JSONResponse(
                        {"error": "Voice generation failed", "details": r.text, "status_code": r.status_code},
                        status_code=500,
                    )
                audio_b64 = base64.b64encode(r.content).decode("utf-8")
                return JSONResponse({"audio_base64": audio_b64})

    except Exception as e:
        return JSONResponse({"error": "Upstream error", "details": str(e)}, status_code=500)

def _voice_id_for_speaker(s: str) -> str | None:
    s = (s or "").lower()
    if s == "orion":
        return ORION_VOICE_ID
    if s == "lyric":
        return LYRIC_VOICE_ID
    return None

@router.post("")
async def speak(req: VoiceRequest):
    """
    POST /voice
    Returns JSON: { "audio_base64": "<...>" }
    """
    speaker = (req.speaker or "").lower()
    text = (req.text or "").strip()
    if not text or text.lower() == "auto":
        text = await _maybe_generate_text_with_gpt(speaker)

    vid = _voice_id_for_speaker(speaker)
    return await _elevenlabs_base(text, vid, as_stream=False)

@router.post("/stream")
async def speak_stream(req: VoiceRequest):
    """
    POST /voice/stream
    Returns audio/mpeg as a streaming response (no JSON).
    """
    speaker = (req.speaker or "").lower()
    text = (req.text or "").strip()
    if not text or text.lower() == "auto":
        text = await _maybe_generate_text_with_gpt(speaker)

    vid = _voice_id_for_speaker(speaker)
    resp = await _elevenlabs_base(text, vid, as_stream=True)
    return resp
