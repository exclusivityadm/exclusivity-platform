from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from apps.backend.db import get_supabase

router = APIRouter()

# ===== Pydantic models =====
class MerchantUpsert(BaseModel):
    merchant_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None

class BrandSettings(BaseModel):
    merchant_id: str
    domain_allowlist: List[str] = []
    token_name: str = "LUX"
    tier_unit: str = "points"
    primary_color: str = "#111111"
    secondary_color: str = "#999999"
    settings: Dict[str, Any] = {}

class Tier(BaseModel):
    code: str
    name: str
    min_points: int = 0
    benefits: Dict[str, Any] = {}
    sort_order: int = 0

class TierSet(BaseModel):
    merchant_id: str
    tiers: List[Tier] = Field(default_factory=list)

# ===== Endpoints =====

@router.post("/profile")
def upsert_merchant(inb: MerchantUpsert):
    sb = get_supabase()
    if not sb:
        raise HTTPException(501, "Supabase not configured")
    data = {k: v for k, v in inb.dict().items() if v is not None}
    if "merchant_id" in data and data["merchant_id"]:
        # try update by merchant_id
        res = sb.table("merchants").update(data).eq("merchant_id", data["merchant_id"]).execute()
        if not res.data:  # not found -> insert
            res = sb.table("merchants").insert({k: v for k, v in data.items() if k != "merchant_id"}).execute()
        return {"ok": True, "merchant": res.data[0]}
    else:
        # upsert by email if provided
        if "email" in data and data["email"]:
            # try select
            sel = sb.table("merchants").select("*").eq("email", data["email"]).limit(1).execute()
            if sel.data:
                mid = sel.data[0]["merchant_id"]
                res = sb.table("merchants").update({k: v for k, v in data.items() if k != "merchant_id"}).eq("merchant_id", mid).execute()
                return {"ok": True, "merchant": res.data[0]}
        res = sb.table("merchants").insert(data).execute()
        return {"ok": True, "merchant": res.data[0]}

@router.get("/profile")
def get_merchant(merchant_id: Optional[str] = Query(default=None), email: Optional[str] = Query(default=None)):
    sb = get_supabase()
    if not sb:
        raise HTTPException(501, "Supabase not configured")
    if merchant_id:
        res = sb.table("merchants").select("*").eq("merchant_id", merchant_id).limit(1).execute()
    elif email:
        res = sb.table("merchants").select("*").eq("email", email).limit(1).execute()
    else:
        raise HTTPException(400, "merchant_id or email required")
    return {"merchant": res.data[0] if res.data else None}

@router.post("/settings")
def save_settings(inb: BrandSettings):
    sb = get_supabase()
    if not sb:
        raise HTTPException(501, "Supabase not configured")
    payload = inb.dict()
    payload["updated_at"] = "now()"
    res = sb.table("brand_settings").upsert(payload, on_conflict="merchant_id").execute()
    return {"ok": True, "settings": res.data[0]}

@router.get("/settings")
def read_settings(merchant_id: str):
    sb = get_supabase()
    if not sb:
        raise HTTPException(501, "Supabase not configured")
    res = sb.table("brand_settings").select("*").eq("merchant_id", merchant_id).limit(1).execute()
    return {"settings": res.data[0] if res.data else None}

@router.post("/tiers")
def set_tiers(inb: TierSet):
    sb = get_supabase()
    if not sb:
        raise HTTPException(501, "Supabase not configured")
    # wipe & insert (simple baseline)
    sb.table("tiers").delete().eq("merchant_id", inb.merchant_id).execute()
    rows = []
    for t in inb.tiers:
        rows.append({
            "merchant_id": inb.merchant_id,
            "code": t.code,
            "name": t.name,
            "min_points": t.min_points,
            "benefits": t.benefits,
            "sort_order": t.sort_order,
        })
    if rows:
        sb.table("tiers").insert(rows).execute()
    res = sb.table("tiers").select("*").eq("merchant_id", inb.merchant_id).order("min_points").execute()
    return {"ok": True, "tiers": res.data}

@router.get("/tiers")
def get_tiers(merchant_id: str):
    sb = get_supabase()
    if not sb:
        raise HTTPException(501, "Supabase not configured")
    res = sb.table("tiers").select("*").eq("merchant_id", merchant_id).order("min_points").execute()
    return {"tiers": res.data}
