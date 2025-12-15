from fastapi import APIRouter
from pydantic import BaseModel, Field

from .orion import Persona

router = APIRouter(prefix="/ai", tags=["ai"])


class AIChatRequest(BaseModel):
    persona: Persona = Field(default=Persona.ORION)
    message: str = Field(..., min_length=1)


@router.post("/chat")
async def chat(payload: AIChatRequest):
    return {
        "ok": True,
        "persona": payload.persona,
        "response": "AI service not yet wired",
    }
