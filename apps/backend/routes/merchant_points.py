# apps/backend/routes/merchant_points.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from apps.backend.db import get_supabase
import os

router = APIRouter()

class PointsConfigIn(BaseModel):
    merchant_id: str
    points_per_usd: Optional[float] = None

@router.get("/config")
def get_config(merchant_id: str):
    sb = get_supabase()
    if not sb:
        raise HTTPException(501, "Supabase not configured")
    row = sb.table("brand_settings").select("points_per_usd").eq("merchant_id", merchant_id).limit(1).execute().data
    if row:
        return {"merchant_id": merchant_id, "points_per_usd": float(row[0].get("points_per_usd", 1.0))}
    # fallback to env default if settings row not present yet
    return {"merchant_id": merchant_id, "points_per_usd": float(os.getenv("POINTS_PER_USD_DEFAULT", "1"))}

@router.post("/config")
def set_config(inb: PointsConfigIn):
    sb = get_supabase()
    if not sb:
        raise HTTPException(501, "Supabase not configured")
    if inb.points_per_usd is None:
        raise HTTPException(400, "points_per_usd is required")
    payload = {"merchant_id": inb.merchant_id, "points_per_usd": float(inb.points_per_usd), "updated_at": "now()"}
    res = sb.table("brand_settings").upsert(payload, on_conflict="merchant_id").execute()
    return {"ok": True, "points_per_usd": float(res.data[0]["points_per_usd"])}
