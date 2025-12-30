# apps/backend/routes/onboarding.py
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from apps.backend.db import get_supabase

log = logging.getLogger("exclusivity.onboarding")

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# -------------------------
# Helpers
# -------------------------

def _coerce_uuid(value: str) -> str:
    """
    Accepts a uuid-ish string and returns canonical string form.
    Raises 400 on invalid UUID.
    """
    try:
        return str(uuid.UUID(str(value).strip()))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid merchant_id (must be UUID)")


def _ensure_merchant_shell(sb, merchant_id: str) -> Dict[str, Any]:
    """
    AUTO mode: if merchant doesn't exist, create a minimal merchant shell.

    Assumes public.merchants has at least:
      - id (uuid PK)
      - created_at (timestamptz default now())
    Other columns may exist (shop_domain, plan, etc). We only set id.
    """
    r = sb.table("merchants").select("*").eq("id", merchant_id).limit(1).execute()
    if r.data:
        return r.data[0]

    # Create minimal shell. If your merchants table requires other NOT NULL cols,
    # Supabase will return an error and you'll see it in logs.
    ins = sb.table("merchants").insert({"id": merchant_id}).execute()
    if not ins.data:
        raise HTTPException(status_code=500, detail="Failed to create merchant shell")
    log.info("Created merchant shell for merchant_id=%s", merchant_id)
    return ins.data[0]


def _ensure_brand_row(sb, merchant_id: str) -> Dict[str, Any]:
    """
    Ensures a merchant_brand row exists (1:1 with merchant).
    This table exists in your Supabase instance per table listing.
    """
    r = sb.table("merchant_brand").select("*").eq("merchant_id", merchant_id).limit(1).execute()
    if r.data:
        return r.data[0]

    payload = {
        "merchant_id": merchant_id,
        "program_name": "Loyalty Program",
        "unit_name_singular": "Point",
        "unit_name_plural": "Points",
        "onboarding_completed": False,
    }
    ins = sb.table("merchant_brand").insert(payload).execute()
    if not ins.data:
        raise HTTPException(status_code=500, detail="Failed to create merchant_brand row")
    log.info("Created merchant_brand row for merchant_id=%s", merchant_id)
    return ins.data[0]


def _safe_merge_tone(existing: Any, incoming: Dict[str, str], avoid_words: Optional[str]) -> Dict[str, Any]:
    """
    tone_tags is expected to be json/jsonb. We keep it flexible.
    """
    base: Dict[str, Any] = {}
    if isinstance(existing, dict):
        base = dict(existing)
    base.update(incoming or {})
    if avoid_words:
        base["avoid_words"] = avoid_words
    return base


# -------------------------
# Routes
# -------------------------

@router.get("/questions")
async def onboarding_questions(merchant_id: str):
    """
    AI-led onboarding questions (Orion/Lyric will ask these in the UI).
    AUTO mode:
      - Ensures merchant exists (creates shell if missing)
      - Ensures merchant_brand row exists
    """
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    mid = _coerce_uuid(merchant_id)

    # AUTO behavior
    _ensure_merchant_shell(sb, mid)
    brand = _ensure_brand_row(sb, mid)

    questions = [
        {"id": "brand_name", "q": "What should we call your brand inside Exclusivity?", "default": brand.get("brand_name") or ""},
        {"id": "program_name", "q": "What do you want to call your loyalty system?", "default": brand.get("program_name") or "Loyalty Program"},
        {"id": "unit_name_singular", "q": "What should one unit be called? (e.g., Point, Credit, Mile)", "default": brand.get("unit_name_singular") or "Point"},
        {"id": "unit_name_plural", "q": "What should multiple units be called?", "default": brand.get("unit_name_plural") or "Points"},
        {"id": "tone_tags", "q": "Describe your brand tone in a few words (e.g., minimal, luxury, warm, bold).", "default": brand.get("tone_tags") or {}},
        {"id": "avoid_words", "q": "Any words we should avoid in copy?", "default": (brand.get("tone_tags") or {}).get("avoid_words", "")},
    ]
    return JSONResponse(content={"ok": True, "merchant_id": mid, "questions": questions})


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
        raise HTTPException(status_code=500, detail="Supabase not configured")

    mid = _coerce_uuid(payload.merchant_id)

    # AUTO behavior
    _ensure_merchant_shell(sb, mid)
    brand = _ensure_brand_row(sb, mid)

    update: Dict[str, Any] = {}

    # Simple scalar fields (only set if provided)
    if payload.brand_name is not None:
        update["brand_name"] = payload.brand_name
    if payload.program_name is not None:
        update["program_name"] = payload.program_name
    if payload.unit_name_singular is not None:
        update["unit_name_singular"] = payload.unit_name_singular
    if payload.unit_name_plural is not None:
        update["unit_name_plural"] = payload.unit_name_plural

    # tone_tags (json/jsonb)
    merged_tone = _safe_merge_tone(brand.get("tone_tags"), payload.tone_tags, payload.avoid_words)
    update["tone_tags"] = merged_tone

    if not update:
        return {"ok": True, "merchant_id": mid, "saved": []}

    sb.table("merchant_brand").update(update).eq("merchant_id", mid).execute()
    return {"ok": True, "merchant_id": mid, "saved": list(update.keys())}


@router.post("/complete")
async def onboarding_complete(merchant_id: str):
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    mid = _coerce_uuid(merchant_id)

    # AUTO behavior
    _ensure_merchant_shell(sb, mid)
    _ensure_brand_row(sb, mid)

    sb.table("merchant_brand").update({"onboarding_completed": True}).eq("merchant_id", mid).execute()
    return {"ok": True, "merchant_id": mid, "onboarding_completed": True}
