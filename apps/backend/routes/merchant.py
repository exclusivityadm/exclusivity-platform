# apps/backend/routes/merchant.py
# =====================================================
# Exclusivity Backend — Merchant Routes (Canonical)
#
# Canonical Rules:
# - merchant_id (UUID) is the ONLY internal identifier
# - shop_domain is an external resolver key
# - /merchant/resolve is the single source of truth
# - /merchant/profile assumes existence
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import time

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
    upsert_one,
    new_uuid,
)

router = APIRouter(tags=["merchant"])  # prefix owned by main.py

# -----------------------------------------------------
# CANONICAL RESOLVER — CREATE OR RETURN
# -----------------------------------------------------
@router.get("/resolve")
def resolve_merchant(
    shop_domain: str = Query(..., description="Shopify shop domain"),
):
    """
    Canonical merchant identity resolver.

    Guarantees:
    - Always returns { ok, merchant_id, created }
    - Never 404s
    - Safe to call repeatedly
    """

    shop = (shop_domain or "").strip().lower()
    if not shop:
        return {"ok": False, "error": "Missing shop_domain"}

    try:
        existing = select_one(
            "merchants",
            {"shop_domain": shop},
            columns="merchant_id",
        )

        if existing and existing.get("merchant_id"):
            return {
                "ok": True,
                "merchant_id": existing["merchant_id"],
                "created": False,
            }

        merchant_id = new_uuid()
        now = int(time.time())

        upsert_one(
            table="merchants",
            conflict_cols="shop_domain",
            row={
                "merchant_id": merchant_id,
                "shop_domain": shop,
                "installed": False,
                "created_at": now,
                "updated_at": now,
            },
        )

        return {
            "ok": True,
            "merchant_id": merchant_id,
            "created": True,
        }

    except SupabaseAdminError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"merchant/resolve error: {e}"}


# -----------------------------------------------------
# PROFILE — ASSUMES MERCHANT EXISTS
# -----------------------------------------------------
@router.get("/profile")
def merchant_profile(shop_domain: str):
    """
    Fetch merchant profile AFTER resolution.
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
            raise HTTPException(404, "Merchant not found")

        return {
            "ok": True,
            "merchant_id": m["merchant_id"],
            "shop_domain": m["shop_domain"],
            "installed": bool(m.get("installed", True)),
            "created_at": m.get("created_at"),
            "updated_at": m.get("updated_at"),
        }

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"merchant/profile error: {e}")


# -----------------------------------------------------
# SETTINGS (STABLE STUB)
# -----------------------------------------------------
@router.get("/settings")
def merchant_settings(merchant_id: str):
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")
    return {"ok": True, "merchant_id": merchant_id, "settings": {}}


# -----------------------------------------------------
# TIERS (STABLE STUB)
# -----------------------------------------------------
@router.get("/tiers")
def merchant_tiers(merchant_id: str):
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")
    return {"ok": True, "merchant_id": merchant_id, "tiers": []}
