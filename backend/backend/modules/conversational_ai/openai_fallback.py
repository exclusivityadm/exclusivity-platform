import httpx
from ...config import settings

OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"

async def tts_fallback(text: str, voice: str = "alloy") -> bytes:
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.OPENAI_TTS_MODEL or "gpt-4o-mini-tts",
        "input": text,
        "voice": voice,
        "format": "mp3"
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OPENAI_TTS_URL, headers=headers, json=payload)
        r.raise_for_status()
        return r.content
