# apps/backend/routes/merchant.py
# =====================================================
# Exclusivity Backend — Merchant Routes (Canonical)
#
# Routes:
#   GET /merchant/profile?shop_domain=...
#   GET /merchant/status?shop_domain=...
#   GET /merchant/settings?merchant_id=...
#   GET /merchant/tiers?merchant_id=...
#
# Source of truth:
#   merchants.install_state (enum)
#
# States:
#   created | oauth_complete | backfill_pending | backfill_running | ready | error
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Any, Dict, Optional

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
)

router = APIRouter(tags=["merchant"])  # prefix owned by main.py


def _normalize_shop_domain(shop_domain: str) -> str:
    return (shop_domain or "").strip().lower()


def _installed_from_state(state: Optional[str], legacy_installed: Optional[bool]) -> bool:
    """
    Canonical: installed = state == ready
    Legacy fallback: installed boolean if state missing
    """
    if state:
        return state == "ready"
    return bool(legacy_installed) if legacy_installed is not None else False


@router.get("/profile")
def merchant_profile(shop_domain: str):
    """
    Resolve canonical merchant identity by shop domain.
    Returns merchant_id (Exclusivity UUID) as the primary key.
    """
    shop_domain = _normalize_shop_domain(shop_domain)
    if not shop_domain:
        raise HTTPException(400, "Missing shop_domain")

    try:
        m = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,install_state,install_error,oauth_completed_at,ready_at,created_at,updated_at",
        )

        if not m:
            # Frontend treats this as "not yet installed"
            raise HTTPException(404, "Merchant not found for shop_domain")

        state = m.get("install_state")
        legacy_installed = m.get("installed")

        return {
            "ok": True,
            "merchant_id": m.get("merchant_id"),
            "shop_domain": m.get("shop_domain"),
            # Canonical:
            "install_state": state or "created",
            "install_error": m.get("install_error"),
            "installed": _installed_from_state(state, legacy_installed),
            "oauth_completed_at": m.get("oauth_completed_at"),
            "ready_at": m.get("ready_at"),
            "created_at": m.get("created_at"),
            "updated_at": m.get("updated_at"),
        }

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"merchant/profile error: {e}")


@router.get("/status")
def merchant_status(shop_domain: str):
    """
    Lightweight status endpoint for onboarding + dashboard gating.
    """
    shop_domain = _normalize_shop_domain(shop_domain)
    if not shop_domain:
        raise HTTPException(400, "Missing shop_domain")

    try:
        m = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,install_state,install_error,oauth_completed_at,ready_at,created_at,updated_at",
        )

        if not m:
            return {
                "ok": True,
                "exists": False,
                "shop_domain": shop_domain,
                "install_state": "created",
                "installed": False,
            }

        state = m.get("install_state")
        legacy_installed = m.get("installed")
        installed = _installed_from_state(state, legacy_installed)

        return {
            "ok": True,
            "exists": True,
            "merchant_id": m.get("merchant_id"),
            "shop_domain": m.get("shop_domain"),
            "install_state": state or ("ready" if installed else "created"),
            "install_error": m.get("install_error"),
            "installed": installed,
            "oauth_completed_at": m.get("oauth_completed_at"),
            "ready_at": m.get("ready_at"),
            "created_at": m.get("created_at"),
            "updated_at": m.get("updated_at"),
        }

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"merchant/status error: {e}")


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
