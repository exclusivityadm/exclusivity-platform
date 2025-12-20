from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from apps.backend.db import get_supabase
from apps.backend.services.shopify_backfill import run_backfill_once


router = APIRouter(prefix="/shopify", tags=["shopify"])


@router.get("/backfill/status")
async def backfill_status(merchant_id: str):
    sb = get_supabase()
    if not sb:
        raise HTTPException(500, "Supabase not configured")
    r = sb.table("backfill_runs").select("*").eq("merchant_id", merchant_id).eq("provider", "shopify").limit(1).execute()
    if not r.data:
        return JSONResponse(content={"ok": True, "merchant_id": merchant_id, "status": "none"})
    run = r.data[0]
    return JSONResponse(content={
        "ok": True,
        "merchant_id": merchant_id,
        "status": run.get("status"),
        "orders_processed": run.get("orders_processed"),
        "customers_seen": run.get("customers_seen"),
        "cursor_present": bool(run.get("cursor")),
        "error": run.get("error"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
    })


@router.post("/backfill/pump")
async def backfill_pump(merchant_id: str, background: BackgroundTasks):
    """
    Runs one page of backfill in the background.
    Call repeatedly until status=completed.
    In production we can schedule automatically; for dev store this is perfect.
    """
    background.add_task(run_backfill_once, merchant_id)
    return {"ok": True, "merchant_id": merchant_id, "message": "Backfill page queued."}
