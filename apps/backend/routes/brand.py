# apps/backend/routes/brand.py
# =====================================================
# Exclusivity Backend — Brand Routes (Canonical)
#
# Routes:
#   GET  /brand/status?shop_domain=...
#   POST /brand/ingest                -> bootstrap merchant identity (UUID-first)
#
# Notes:
# - Canonical identity is Exclusivity UUID (merchant_id).
# - shop_domain is integration metadata only.
# - This file is intentionally engine-first and minimal.
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
    upsert_one,
    new_uuid,
)

router = APIRouter(tags=["brand"])  # prefix owned by main.py


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BrandIngestIn(BaseModel):
    shop_domain: str


@router.get("/status")
def brand_status(shop_domain: str):
    """
    Returns install/bootstrap visibility for a given shop_domain.
    This is used by frontend install/onboarding gating.
    """
    try:
        m = select_one("merchants", {"shop_domain": shop_domain}, columns="merchant_id,shop_domain,created_at,updated_at")
        if not m:
            return {
                "ok": True,
                "shop_domain": shop_domain,
                "installed": False,
                "merchant_id": None,
                "backfill_state": "not_started",
            }

        return {
            "ok": True,
            "shop_domain": m.get("shop_domain"),
            "installed": True,
            "merchant_id": m.get("merchant_id"),
            # Backfill state will be hardened later (UI-07/08). For now stable.
            "backfill_state": "unknown",
        }
    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"brand/status error: {e}")


@router.post("/ingest")
def brand_ingest(payload: BrandIngestIn):
    """
    Bootstrap endpoint: guarantees a merchant exists for this shop_domain and returns merchant_id.
    Idempotent by shop_domain.
    """
    shop_domain = (payload.shop_domain or "").strip().lower()
    if not shop_domain:
        raise HTTPException(400, "Missing shop_domain")

    try:
        existing = select_one("merchants", {"shop_domain": shop_domain}, columns="merchant_id,shop_domain")
        if existing and existing.get("merchant_id"):
            return {
                "ok": True,
                "created": False,
                "shop_domain": shop_domain,
                "merchant_id": existing.get("merchant_id"),
            }

        merchant_id = new_uuid()
        row: Dict[str, Any] = {
            "merchant_id": merchant_id,
            "shop_domain": shop_domain,
            "installed": True,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }

        # Upsert guarantees idempotency by shop_domain
        out = upsert_one("merchants", row, conflict_cols="shop_domain")
        mid = out.get("merchant_id") or merchant_id

        return {
            "ok": True,
            "created": True,
            "shop_domain": shop_domain,
            "merchant_id": mid,
        }

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"brand/ingest error: {e}")
