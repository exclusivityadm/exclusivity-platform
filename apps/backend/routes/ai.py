from __future__ import annotations

import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .services.ai_brand_brain import AIBrandBrain
from .orion import Persona


router = APIRouter(prefix="/ai", tags=["ai"])


class AIChatRequest(BaseModel):
    persona: Persona = Field(default=Persona.ORION)
    message: str = Field(..., min_length=1)
    merchant: Dict[str, Any] = Field(default_factory=dict)
    program: Dict[str, Any] = Field(default_factory=dict)


@router.post("/chat")
async def ai_chat(payload: AIChatRequest):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=501, detail="AI not configured")

    brain = AIBrandBrain(persona=payload.persona)
    return await brain.respond(
        message=payload.message,
        merchant=payload.merchant,
        program=payload.program,
    )
