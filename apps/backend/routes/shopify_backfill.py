from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.backend.services.shopify_backfill import LEGACY_BACKFILL_BLOCK_REASON


router = APIRouter(prefix="/shopify", tags=["shopify"])


@router.get("/backfill/status")
async def backfill_status(merchant_id: str):
    # Legacy endpoint accepted any arbitrary merchant_id without authentication,
    # potentially leaking other merchants' import metrics. Do not expose data
    # until tenant-authorization is implemented.
    raise HTTPException(status_code=503, detail=LEGACY_BACKFILL_BLOCK_REASON)


@router.post("/backfill/pump")
async def backfill_pump(merchant_id: str):
    # Do not queue a job that can rewrite loyalty history or trigger background
    # vendor usage. Replace with an authenticated audited import pipeline.
    raise HTTPException(status_code=503, detail=LEGACY_BACKFILL_BLOCK_REASON)
