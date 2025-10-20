import httpx
from typing import Optional
from ...config import settings

ELEVEN_API = "https://api.elevenlabs.io/v1"

async def _resolve_voice_id(client: httpx.AsyncClient, voice_pref: str) -> Optional[str]:
    # If user supplied an ID (looks like uuid), just return it
    if "-" in voice_pref or len(voice_pref) > 20:
        return voice_pref
    # else treat as name: fetch and match
    r = await client.get(f"{ELEVEN_API}/voices", headers={"xi-api-key": settings.ELEVENLABS_API_KEY})
    r.raise_for_status()
    data = r.json()
    for v in data.get("voices", []):
        if v.get("name","").lower() == voice_pref.lower():
            return v.get("voice_id")
    # default fallbacks
    for fallback_name in ["Adam", "Rachel", "Alloy", "Amber"]:
        for v in data.get("voices", []):
            if v.get("name","").lower() == fallback_name.lower():
                return v.get("voice_id")
    return None

async def synthesize_voice(text: str, voice_pref: str) -> bytes:
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=60) as client:
        voice_id = await _resolve_voice_id(client, voice_pref or "Adam")
        if not voice_id:
            raise RuntimeError("No matching ElevenLabs voice found.")
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.75}
        }
        r = await client.post(f"{ELEVEN_API}/text-to-speech/{voice_id}", headers=headers, json=payload)
        r.raise_for_status()
        return r.content
