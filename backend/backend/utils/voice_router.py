# backend/backend/utils/voice_router.py
from dataclasses import dataclass
import os

@dataclass
class CharacterConfig:
    engine: str  # "elevenlabs" or "openai"
    gender: str  # "male" or "female"
    voice_id: str | None  # engine-specific voice id/name

def get_character_config(character: str) -> CharacterConfig:
    ch = (character or "").strip().lower()
    if ch in ("orion", "o"):
        # Orion = male
        # Prefer explicit ElevenLabs voice id; else try OPENAI voice name
        return CharacterConfig(
            engine=os.getenv("TTS_PREFERRED_ENGINE", "elevenlabs"),
            gender="male",
            voice_id=os.getenv("ELEVENLABS_VOICE_ORION") or os.getenv("OPENAI_VOICE_ORION")
        )
    # default to Lyric (female)
    return CharacterConfig(
        engine=os.getenv("TTS_PREFERRED_ENGINE", "elevenlabs"),
        gender="female",
        voice_id=os.getenv("ELEVENLABS_VOICE_LYRIC") or os.getenv("OPENAI_VOICE_LYRIC")
    )

def pick_openai_voice_for_gender(gender: str) -> str:
    """
    Map gender to an OpenAI TTS 'voice' name. You can customize as you like.
    """
    male = os.getenv("OPENAI_VOICE_ORION", "alloy")
    female = os.getenv("OPENAI_VOICE_LYRIC", "verse")
    return male if gender == "male" else female
