# apps/backend/routes/merchant.py
# =====================================================
# Exclusivity Backend — Merchant Routes (Drop C Canonical)
#
# Routes:
#   GET /merchant/profile?shop_domain=...
#   GET /merchant/settings?merchant_id=...
#   GET /merchant/tiers?merchant_id=...
#
# Contract rule:
#   - Expected states return 200 with { ok: false, message, code }
#   - Unexpected errors return 200 with { ok: false, message: "..." }
#   - Never rely on thrown exceptions for normal install flow
# =====================================================

from __future__ import annotations

from fastapi import APIRouter
from typing import Any, Dict, Optional

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
)

router = APIRouter(tags=["merchant"])  # prefix owned by main.py


def ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, **data}


def fail(message: str, code: str = "ERROR", details: Any | None = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "message": message, "code": code}
    if details is not None:
        out["details"] = details
    return out


@router.get("/profile")
def merchant_profile(shop_domain: str):
    """
    Resolve canonical merchant identity by shop domain.
    """
    shop_domain = (shop_domain or "").strip().lower()
    if not shop_domain:
        return fail("Missing shop_domain", code="MISSING_SHOP_DOMAIN")

    try:
        m = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,created_at,updated_at",
        )

        if not m:
            # Normal state during onboarding if merchant row not created yet
            return fail("Merchant not found for shop_domain", code="MERCHANT_NOT_FOUND")

        merchant_id = m.get("merchant_id")
        if not merchant_id:
            return fail("Merchant record missing merchant_id", code="MERCHANT_INVALID")

        return ok(
            {
                "merchant_id": merchant_id,
                "shop_domain": m.get("shop_domain") or shop_domain,
                "installed": bool(m.get("installed")) if m.get("installed") is not None else True,
                "created_at": m.get("created_at"),
                "updated_at": m.get("updated_at"),
            }
        )

    except SupabaseAdminError as e:
        return fail("Supabase error resolving merchant profile", code="SUPABASE_ERROR", details=str(e))
    except Exception as e:
        return fail("merchant/profile error", code="UNEXPECTED", details=str(e))


@router.get("/settings")
def merchant_settings(merchant_id: str):
    if not merchant_id:
        return fail("Missing merchant_id", code="MISSING_MERCHANT_ID")
    # Expanded in Drop D+ if needed; Drop C keeps contract stable
    return ok({"merchant_id": merchant_id, "settings": {}})


@router.get("/tiers")
def merchant_tiers(merchant_id: str):
    if not merchant_id:
        return fail("Missing merchant_id", code="MISSING_MERCHANT_ID")
    # Expanded in Drop D+ if needed; Drop C keeps contract stable
    return ok({"merchant_id": merchant_id, "tiers": []})
