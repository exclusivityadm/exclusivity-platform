from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from apps.backend.routes.services.pricing_engine_service import (
    create_catalog_snapshot,
    generate_recommendations,
    latest_recommendation_for_merchant,
    recommendation_items,
)

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/catalog/snapshot")
async def pricing_catalog_snapshot(body: Dict[str, Any]):
    """
    Stores a point-in-time catalog snapshot.
    Engine-first: snapshot can be created by Shopify ingest, brand ingest, or admin tooling.
    """
    merchant_id = body.get("merchant_id")
    if not merchant_id:
        raise HTTPException(status_code=400, detail="missing_merchant_id")

    source = body.get("source") or "manual"
    notes = body.get("notes")
    items = body.get("items") or []
    if not isinstance(items, list) or len(items) == 0:
        raise HTTPException(status_code=400, detail="missing_items")

    snap = create_catalog_snapshot(
        merchant_id=str(merchant_id),
        source=str(source),
        notes=str(notes) if notes is not None else None,
        items=items,
    )
    return {"ok": True, "snapshot": snap}


@router.post("/recommendations/generate")
async def pricing_recommendations_generate(body: Dict[str, Any]):
    """
    Generates pricing recommendations for a snapshot.
    """
    merchant_id = body.get("merchant_id")
    snapshot_id = body.get("snapshot_id")
    if not merchant_id or not snapshot_id:
        raise HTTPException(status_code=400, detail="missing_merchant_id_or_snapshot_id")

    uplift_percent = body.get("uplift_percent")  # optional override
    buffer_cents = body.get("buffer_cents")      # optional override
    est_mint_cost_cents = body.get("est_mint_cost_cents")  # optional override

    out = generate_recommendations(
        merchant_id=str(merchant_id),
        snapshot_id=str(snapshot_id),
        uplift_percent=uplift_percent,
        buffer_cents=buffer_cents,
        est_mint_cost_cents=est_mint_cost_cents,
    )
    return {"ok": True, "recommendation": out}


@router.get("/recommendations/latest")
async def pricing_recommendations_latest(merchant_id: str = Query(...)):
    """
    Returns latest recommendation set + items for merchant_id.
    """
    rec = latest_recommendation_for_merchant(str(merchant_id))
    if not rec:
        return {"ok": True, "recommendation": None}

    items = recommendation_items(rec["id"])
    return {
        "ok": True,
        "recommendation": rec,
        "items": items,
    }
