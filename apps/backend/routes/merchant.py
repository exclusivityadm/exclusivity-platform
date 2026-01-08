# apps/backend/routes/merchant.py
# =====================================================
# Exclusivity Backend — Merchant Routes (Canonical)
# =====================================================

from fastapi import APIRouter, HTTPException
from apps.backend.contracts.api import api_ok, api_error
from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
)

router = APIRouter(tags=["merchant"])


@router.get("/profile")
def merchant_profile(shop_domain: str):
    shop_domain = (shop_domain or "").strip().lower()
    if not shop_domain:
        return api_error(
            "Missing shop_domain",
            code="missing_shop_domain",
        )

    try:
        merchant = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="""
                merchant_id,
                shop_domain,
                installed,
                created_at,
                updated_at
            """,
        )

        if not merchant:
            return api_error(
                "Merchant not found",
                code="merchant_not_found",
            )

        return api_ok(
            {
                "merchant_id": merchant["merchant_id"],
                "shop_domain": merchant["shop_domain"],
                "installed": bool(merchant.get("installed", True)),
                "created_at": merchant.get("created_at"),
                "updated_at": merchant.get("updated_at"),
            }
        )

    except SupabaseAdminError as e:
        return api_error(
            "Supabase error",
            code="supabase_error",
            details=str(e),
        )
    except Exception as e:
        return api_error(
            "Unhandled merchant/profile error",
            code="merchant_profile_exception",
            details=str(e),
        )


@router.get("/settings")
def merchant_settings(merchant_id: str):
    if not merchant_id:
        return api_error(
            "Missing merchant_id",
            code="missing_merchant_id",
        )

    return api_ok(
        {
            "merchant_id": merchant_id,
            "settings": {},
        }
    )


@router.get("/tiers")
def merchant_tiers(merchant_id: str):
    if not merchant_id:
        return api_error(
            "Missing merchant_id",
            code="missing_merchant_id",
        )

    return api_ok(
        {
            "merchant_id": merchant_id,
            "tiers": [],
        }
    )
