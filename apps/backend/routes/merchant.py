# apps/backend/routes/merchant.py
# =====================================================
# Exclusivity Backend — Merchant Routes (Canonical)
#
# Routes:
#   GET /merchant/profile?shop_domain=...
#   GET /merchant/settings?merchant_id=...
#   GET /merchant/tiers?merchant_id=...
#
# Engine-first: profile resolution is required for install flow (UI-05/06).
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
)

router = APIRouter(tags=["merchant"])  # prefix owned by main.py


@router.get("/profile")
def merchant_profile(shop_domain: str):
    """
    Resolve canonical merchant identity by shop domain.
    Returns merchant_id (Exclusivity UUID) as the primary key.
    """
    shop_domain = (shop_domain or "").strip().lower()
    if not shop_domain:
        raise HTTPException(400, "Missing shop_domain")

    try:
        m = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,created_at,updated_at",
        )
        if not m:
            # Frontend treats this as "not yet installed"
            raise HTTPException(404, "Merchant not found for shop_domain")

        # Canonical response shape:
        return {
            "ok": True,
            "merchant_id": m.get("merchant_id"),
            "shop_domain": m.get("shop_domain"),
            "installed": bool(m.get("installed")) if m.get("installed") is not None else True,
            "created_at": m.get("created_at"),
            "updated_at": m.get("updated_at"),
        }

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"merchant/profile error: {e}")


@router.get("/settings")
def merchant_settings(merchant_id: str):
    """
    Minimal stable shape. Expanded later.
    """
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")
    return {"ok": True, "merchant_id": merchant_id, "settings": {}}


@router.get("/tiers")
def merchant_tiers(merchant_id: str):
    """
    Minimal stable shape. Expanded later.
    """
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")
    return {"ok": True, "merchant_id": merchant_id, "tiers": []}
