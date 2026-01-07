# apps/backend/routes/merchant.py
# =====================================================
# Exclusivity Backend — Merchant Routes (Canonical)
#
# Routes:
#   GET /merchant/profile?shop_domain=...
#   GET /merchant/settings?merchant_id=...
#   GET /merchant/tiers?merchant_id=...
#
# Response shape is now standardized:
#   { ok: true, data: {...} }
#   { ok: false, error: "..." , details?: ... }
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
)

from apps.backend.routes.services.api_result import ok, err

router = APIRouter(tags=["merchant"])  # prefix owned by main.py


@router.get("/profile")
def merchant_profile(shop_domain: str):
    """
    Resolve canonical merchant identity by shop domain.
    Returns merchant_id (Exclusivity UUID) inside `data`.
    """
    shop_domain = (shop_domain or "").strip().lower()
    if not shop_domain:
        # Keep HTTP status semantics for callers that rely on it
        raise HTTPException(status_code=400, detail="Missing shop_domain")

    try:
        m = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,created_at,updated_at",
        )

        if not m:
            # IMPORTANT: frontend can treat as "not installed yet"
            return err("Merchant not found for shop_domain", {"shop_domain": shop_domain})

        data = {
            "merchant_id": m.get("merchant_id"),
            "shop_domain": m.get("shop_domain"),
            "installed": bool(m.get("installed")) if m.get("installed") is not None else True,
            "created_at": m.get("created_at"),
            "updated_at": m.get("updated_at"),
        }
        return ok(data)

    except SupabaseAdminError as e:
        return err("Supabase error", {"message": str(e)})
    except Exception as e:
        return err("merchant/profile error", {"message": str(e)})


@router.get("/settings")
def merchant_settings(merchant_id: str):
    """
    Minimal stable shape. Expanded later.
    """
    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(status_code=400, detail="Missing merchant_id")

    # Later: fetch settings table
    return ok({"merchant_id": merchant_id, "settings": {}})


@router.get("/tiers")
def merchant_tiers(merchant_id: str):
    """
    Minimal stable shape. Expanded later.
    """
    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(status_code=400, detail="Missing merchant_id")

    # Later: fetch tiers table
    return ok({"merchant_id": merchant_id, "tiers": []})
