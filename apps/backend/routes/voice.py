from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str = Field(default="default")


class VoiceResponse(BaseModel):
    ok: bool
    audio_url: str


@router.post("/speak", response_model=VoiceResponse)
async def speak(payload: VoiceRequest) -> VoiceResponse:
    """
    Voice synthesis placeholder.

    This route is intentionally stubbed until a concrete
    voice service implementation is introduced under
    routes/services/.
    """
    return VoiceResponse(ok=True, audio_url="")
