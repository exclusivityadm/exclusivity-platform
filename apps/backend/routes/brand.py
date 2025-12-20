from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from apps.backend.db import get_supabase

router = APIRouter(tags=["brand"])


@router.get("/status")
async def brand_status(merchant_id: str):
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    r = sb.table("merchant_brand").select("*").eq("merchant_id", merchant_id).limit(1).execute()
    if not r.data:
        return JSONResponse(content={"ok": True, "merchant_id": merchant_id, "exists": False})

    row = r.data[0]
    return JSONResponse(content={
        "ok": True,
        "merchant_id": merchant_id,
        "exists": True,
        "shop_domain": row.get("shop_domain"),
        "brand_name": row.get("brand_name"),
        "primary_color": row.get("primary_color"),
        "secondary_color": row.get("secondary_color"),
        "font_family": row.get("font_family"),
        "program_name": row.get("program_name"),
        "unit_name_singular": row.get("unit_name_singular"),
        "unit_name_plural": row.get("unit_name_plural"),
        "onboarding_completed": row.get("onboarding_completed"),
    })


@router.post("/ingest")
async def brand_ingest(merchant_id: str, background: BackgroundTasks):
    try:
        from apps.backend.services.shopify_brand_ingest import ingest_brand  # type: ignore
        background.add_task(ingest_brand, merchant_id)
        return {"ok": True, "merchant_id": merchant_id, "message": "Brand ingestion queued."}
    except Exception as e:
        raise HTTPException(500, f"Brand ingestion service not available: {e}")
