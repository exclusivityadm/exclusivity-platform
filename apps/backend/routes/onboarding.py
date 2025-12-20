from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Optional

from apps.backend.db import get_supabase


router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _ensure_brand_row(sb, merchant_id: str):
    r = sb.table("merchant_brand").select("*").eq("merchant_id", merchant_id).limit(1).execute()
    if r.data:
        return r.data[0]
    ins = sb.table("merchant_brand").insert({
        "merchant_id": merchant_id,
        "program_name": "Loyalty Program",
        "unit_name_singular": "Point",
        "unit_name_plural": "Points",
        "onboarding_completed": False,
    }).execute()
    return ins.data[0]


@router.get("/questions")
async def onboarding_questions(merchant_id: str):
    """
    AI-led onboarding questions (Orion/Lyric will ask these in the UI).
    Theme ingestion happens in a separate step (we store results back onto merchant_brand).
    """
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    brand = _ensure_brand_row(sb, merchant_id)

    questions = [
        {"id": "brand_name", "q": "What should we call your brand inside Exclusivity?", "default": brand.get("brand_name") or ""},
        {"id": "program_name", "q": "What do you want to call your loyalty system?", "default": brand.get("program_name") or "Loyalty Program"},
        {"id": "unit_name_singular", "q": "What should one unit be called? (e.g., Point, Credit, Mile)", "default": brand.get("unit_name_singular") or "Point"},
        {"id": "unit_name_plural", "q": "What should multiple units be called?", "default": brand.get("unit_name_plural") or "Points"},
        {"id": "tone_tags", "q": "Describe your brand tone in a few words (e.g., minimal, luxury, warm, bold).", "default": ""},
        {"id": "avoid_words", "q": "Any words we should avoid in copy?", "default": ""},
    ]
    return JSONResponse(content={"ok": True, "merchant_id": merchant_id, "questions": questions})


class OnboardingAnswers(BaseModel):
    merchant_id: str
    brand_name: Optional[str] = None
    program_name: Optional[str] = None
    unit_name_singular: Optional[str] = None
    unit_name_plural: Optional[str] = None
    tone_tags: Dict[str, str] = Field(default_factory=dict)
    avoid_words: Optional[str] = None


@router.post("/answers")
async def onboarding_answers(payload: OnboardingAnswers):
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    brand = _ensure_brand_row(sb, payload.merchant_id)

    update = {}
    if payload.brand_name is not None:
        update["brand_name"] = payload.brand_name
    if payload.program_name is not None:
        update["program_name"] = payload.program_name
    if payload.unit_name_singular is not None:
        update["unit_name_singular"] = payload.unit_name_singular
    if payload.unit_name_plural is not None:
        update["unit_name_plural"] = payload.unit_name_plural

    # Store tone tags as jsonb (simple)
    # We also keep "avoid_words" within tone_tags for now to avoid schema creep
    tone = dict(brand.get("tone_tags") or {})
    tone.update(payload.tone_tags or {})
    if payload.avoid_words:
        tone["avoid_words"] = payload.avoid_words
    update["tone_tags"] = tone

    sb.table("merchant_brand").update(update).eq("merchant_id", payload.merchant_id).execute()
    return {"ok": True, "merchant_id": payload.merchant_id, "saved": list(update.keys())}


@router.post("/complete")
async def onboarding_complete(merchant_id: str):
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")
    sb.table("merchant_brand").update({"onboarding_completed": True}).eq("merchant_id", merchant_id).execute()
    return {"ok": True, "merchant_id": merchant_id, "onboarding_completed": True}
