from __future__ import annotations

import os
from typing import Any, Dict, Optional, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.ai.ai_context_builder import AIContextBuilder, Persona


router = APIRouter(prefix="/ai", tags=["ai"])


class AIChatRequest(BaseModel):
    persona: Persona = Field(default="orion")
    message: str = Field(..., min_length=1)

    # The route should be given already-fetched merchant/program objects by upstream deps.
    # For now, accept optional payloads to keep this structurally complete.
    merchant: Dict[str, Any] = Field(default_factory=dict)
    program: Dict[str, Any] = Field(default_factory=dict)


class AIChatResponse(BaseModel):
    persona: Persona
    response: str


def _get_openai_config() -> Dict[str, str]:
    """
    Minimal, self-contained OpenAI-compatible config.
    If you already have a central LLM client, you can remove this and wire it in.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    if not api_key:
        raise HTTPException(
            status_code=501,
            detail="AI is not configured (missing OPENAI_API_KEY).",
        )
    return {"api_key": api_key, "base_url": base_url, "model": model}


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(payload: AIChatRequest) -> AIChatResponse:
    """
    Canonical merchant-copilot endpoint.

    Notes:
    - Avoids crypto terms by policy in AIContextBuilder.
    - Uses a minimal OpenAI-compatible call for structural completeness.
    - Replace with your centralized LLM client if desired.
    """
    cfg = _get_openai_config()

    builder = AIContextBuilder()
    ctx = builder.build(
        persona=payload.persona,
        merchant=payload.merchant,
        program=payload.program,
        request_meta={"route": "/ai/chat"},
    )

    messages = ctx.to_messages(payload.message)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(
                f"{cfg['base_url'].rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {cfg['api_key']}"},
                json={
                    "model": cfg["model"],
                    "messages": messages,
                    "temperature": 0.4,
                },
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"AI upstream error: {str(e)}") from e

    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"AI upstream returned {r.status_code}: {r.text}")

    data = r.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        raise HTTPException(status_code=502, detail="AI response parsing failed.")

    return AIChatResponse(persona=payload.persona, response=content)
