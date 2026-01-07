# apps/backend/routes/merchant.py
# =====================================================
# Exclusivity Backend — Merchant Routes (Canonical)
#
# Routes:
#   GET  /merchant/resolve?shop_domain=...        (canonical)
#   GET  /merchant/profile?shop_domain=...        (legacy stable)
#   GET  /merchant/settings?merchant_id=...
#   GET  /merchant/tiers?merchant_id=...
#
# Goals:
# - Single authoritative merchant identity resolver for install/onboarding.
# - Idempotent: safe to call repeatedly.
# - Consistent response shapes to eliminate frontend typing churn.
#
# Notes:
# - "merchant_id" is the canonical UUID primary key in `public.merchants`.
# - This module assumes the Supabase admin helpers exist and are correct.
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any, Dict, Optional

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
    insert_one,
    update_one,
)

router = APIRouter(tags=["merchant"])  # prefix owned by main.py


def _norm_shop(shop_domain: str) -> str:
    return (shop_domain or "").strip().lower()


def _coalesce_bool(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    return bool(v)


# -----------------------------------------------------
# Canonical resolver (install/onboarding anchor)
# -----------------------------------------------------
@router.get("/resolve")
def merchant_resolve(shop_domain: str, create_if_missing: bool = True) -> Dict[str, Any]:
    """
    Canonical merchant identity resolution.

    Query:
      - shop_domain: required
      - create_if_missing: default true

    Returns (success):
      {
        "ok": true,
        "merchant_id": "<uuid>",
        "shop_domain": "<domain>",
        "created": <bool>,
        "installed": <bool>
      }

    Returns (failure):
      { "ok": false, "error": "..." }
    """
    shop_domain = _norm_shop(shop_domain)
    if not shop_domain:
        raise HTTPException(400, "Missing shop_domain")

    try:
        m = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,created_at,updated_at",
        )

        if m:
            return {
                "ok": True,
                "merchant_id": m.get("merchant_id"),
                "shop_domain": m.get("shop_domain") or shop_domain,
                "created": False,
                "installed": _coalesce_bool(m.get("installed"), default=False),
            }

        if not create_if_missing:
            return {"ok": False, "error": "Merchant not found"}

        # Create minimal merchant row.
        # IMPORTANT: We only write safe baseline fields here.
        created_row = insert_one(
            "merchants",
            {
                "shop_domain": shop_domain,
                "installed": False,
            },
            returning="merchant_id,shop_domain,installed,created_at,updated_at",
        )

        if not created_row or not created_row.get("merchant_id"):
            return {"ok": False, "error": "Failed to create merchant"}

        return {
            "ok": True,
            "merchant_id": created_row.get("merchant_id"),
            "shop_domain": created_row.get("shop_domain") or shop_domain,
            "created": True,
            "installed": _coalesce_bool(created_row.get("installed"), default=False),
        }

    except SupabaseAdminError as e:
        # Consistent error payload (don’t leak internals)
        return {"ok": False, "error": f"Supabase error: {str(e)}"}
    except Exception as e:
        return {"ok": False, "error": f"merchant/resolve error: {e}"}


# -----------------------------------------------------
# Legacy stable shape (used by some frontend screens)
# -----------------------------------------------------
@router.get("/profile")
def merchant_profile(shop_domain: str) -> Dict[str, Any]:
    """
    Stable profile lookup by shop domain.
    If not found, returns 404 like before (frontend can treat as "not installed").
    """
    shop_domain = _norm_shop(shop_domain)
    if not shop_domain:
        raise HTTPException(400, "Missing shop_domain")

    try:
        m = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,created_at,updated_at",
        )
        if not m:
            raise HTTPException(404, "Merchant not found for shop_domain")

        return {
            "ok": True,
            "merchant_id": m.get("merchant_id"),
            "shop_domain": m.get("shop_domain") or shop_domain,
            "installed": _coalesce_bool(m.get("installed"), default=False),
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
def merchant_settings(merchant_id: str) -> Dict[str, Any]:
    """
    Minimal stable shape. Expanded later.
    """
    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")
    return {"ok": True, "merchant_id": merchant_id, "settings": {}}


@router.get("/tiers")
def merchant_tiers(merchant_id: str) -> Dict[str, Any]:
    """
    Minimal stable shape. Expanded later.
    """
    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")
    return {"ok": True, "merchant_id": merchant_id, "tiers": []}
