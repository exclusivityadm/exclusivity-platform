from __future__ import annotations

import os
from typing import Dict

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .services.voice.voice_service import VoiceService


router = APIRouter(prefix="/voice", tags=["voice"])

service = VoiceService()


class VoiceRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str = Field(default="default")


class VoiceResponse(BaseModel):
    ok: bool
    audio_url: str


@router.post("/speak", response_model=VoiceResponse)
async def speak(payload: VoiceRequest) -> VoiceResponse:
    try:
        audio_url = await service.synthesize(
            text=payload.text,
            voice=payload.voice,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return VoiceResponse(ok=True, audio_url=audio_url)
