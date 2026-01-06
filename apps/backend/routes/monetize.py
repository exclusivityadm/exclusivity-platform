from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Query

from apps.backend.routes.services.monetize_service import (
    record_usage_event,
    draft_invoice,
    latest_invoice,
    invoice_lines,
)

router = APIRouter(prefix="/monetize", tags=["monetize"])

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

def _require_admin(x_admin_token: str) -> None:
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

@router.post("/usage/record")
async def monetize_usage_record(
    body: Dict[str, Any],
    x_admin_token: str = Header(default=""),
):
    """
    Records a billable usage event (email/sms/ai_execute/etc).
    Admin-protected to prevent arbitrary merchant charging.
    """
    _require_admin(x_admin_token)

    merchant_id = body.get("merchant_id")
    category = body.get("category")
    item = body.get("item")
    if not merchant_id or not category or not item:
        raise HTTPException(status_code=400, detail="missing_merchant_id_category_item")

    try:
        row = record_usage_event(
            merchant_id=str(merchant_id),
            category=str(category),
            item=str(item),
            quantity=int(body.get("quantity") or 1),
            unit_cost_cents=int(body.get("unit_cost_cents") or 0),
            unit_price_cents=int(body.get("unit_price_cents") or 0),
            source=str(body.get("source") or "engine"),
            source_ref=str(body.get("source_ref")) if body.get("source_ref") else None,
        )
        return {"ok": True, "usage": row}
    except Exception:
        # Idempotent duplicates should be treated as ok for engine callers
        return {"ok": True, "idempotent": True}

@router.post("/invoice/draft")
async def monetize_invoice_draft(
    body: Dict[str, Any],
    x_admin_token: str = Header(default=""),
):
    """
    Drafts (or re-drafts deterministically) an invoice for a period.
    Admin-protected.
    """
    _require_admin(x_admin_token)

    merchant_id = body.get("merchant_id")
    ps = body.get("period_start")
    pe = body.get("period_end")
    if not merchant_id or not ps or not pe:
        raise HTTPException(status_code=400, detail="missing_merchant_id_period")

    out = draft_invoice(
        merchant_id=str(merchant_id),
        period_start=date.fromisoformat(str(ps)),
        period_end=date.fromisoformat(str(pe)),
    )
    return {"ok": True, "invoice": out}

@router.get("/invoice/latest")
async def monetize_invoice_latest(merchant_id: str = Query(...)):
    inv = latest_invoice(str(merchant_id))
    if not inv:
        return {"ok": True, "invoice": None}
    lines = invoice_lines(inv["id"])
    return {"ok": True, "invoice": inv, "lines": lines}
