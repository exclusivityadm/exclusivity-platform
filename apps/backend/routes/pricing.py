from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from apps.backend.db import get_supabase
from apps.backend.services.shopify_catalog_snapshot import snapshot_catalog
from apps.backend.services.pricing_buffer import generate_pricing_recommendations


router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/catalog/snapshot")
async def catalog_snapshot(merchant_id: str, background: BackgroundTasks):
    background.add_task(snapshot_catalog, merchant_id)
    return {"ok": True, "merchant_id": merchant_id, "message": "Catalog snapshot queued."}


@router.post("/recommendations/generate")
async def pricing_generate(merchant_id: str, background: BackgroundTasks):
    background.add_task(generate_pricing_recommendations, merchant_id)
    return {"ok": True, "merchant_id": merchant_id, "message": "Pricing recommendations queued."}


@router.get("/recommendations/latest")
async def pricing_latest(merchant_id: str):
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")

    r = sb.table("merchant_pricing_recommendations")\
        .select("*")\
        .eq("merchant_id", merchant_id)\
        .order("captured_at", desc=True)\
        .limit(1)\
        .execute()

    if not r.data:
        return JSONResponse(content={"ok": True, "merchant_id": merchant_id, "exists": False})

    row = r.data[0]
    return JSONResponse(content={
        "ok": True,
        "merchant_id": merchant_id,
        "exists": True,
        "captured_at": row.get("captured_at"),
        "strategy": row.get("strategy"),
        "buffer_cents": row.get("buffer_cents"),
        "notes": row.get("notes"),
        "payload": row.get("payload"),
    })
