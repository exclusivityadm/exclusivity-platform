# apps/backend/routes/merchant.py
# =====================================================
# Exclusivity Backend — STEP 21
# MERCHANT ROUTES (CONTRACT COMPLIANT)
#
# This file strictly conforms to:
#   apps/backend/contracts/api.py
#
# ❌ No ad-hoc response shapes
# ❌ No implicit keys
# ✅ ApiResponse[T] ONLY
# =====================================================

from __future__ import annotations

from fastapi import APIRouter
from typing import List

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
    select_many,
)

from apps.backend.contracts.api import (
    ApiOk,
    ApiErr,
    ApiResponse,
    MerchantProfile,
    MerchantSettings,
    MerchantTier,
)

router = APIRouter(tags=["merchant"])  # prefix owned by main.py

# -----------------------------------------------------
# GET /merchant/profile
# -----------------------------------------------------
@router.get("/profile", response_model=ApiResponse[MerchantProfile])
def merchant_profile(shop_domain: str):
    shop_domain = (shop_domain or "").strip().lower()
    if not shop_domain:
        return ApiErr(
            code="merchant.invalid",
            message="Missing shop_domain",
        )

    try:
        row = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,created_at,updated_at",
        )

        if not row:
            return ApiErr(
                code="merchant.not_found",
                message="Merchant not found for shop_domain",
            )

        return ApiOk(
            data=MerchantProfile(
                merchant_id=row["merchant_id"],
                shop_domain=row["shop_domain"],
                installed=bool(row.get("installed", True)),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )

    except SupabaseAdminError as e:
        return ApiErr(
            code="internal.error",
            message="Supabase error resolving merchant",
            details={"error": str(e)},
        )

    except Exception as e:
        return ApiErr(
            code="internal.error",
            message="Unexpected merchant/profile error",
            details={"error": str(e)},
        )


# -----------------------------------------------------
# GET /merchant/settings
# -----------------------------------------------------
@router.get("/settings", response_model=ApiResponse[MerchantSettings])
def merchant_settings(merchant_id: str):
    if not merchant_id:
        return ApiErr(
            code="merchant.invalid",
            message="Missing merchant_id",
        )

    return ApiOk(
        data=MerchantSettings(
            merchant_id=merchant_id,
            settings={},
        )
    )


# -----------------------------------------------------
# GET /merchant/tiers
# -----------------------------------------------------
@router.get("/tiers", response_model=ApiResponse[List[MerchantTier]])
def merchant_tiers(merchant_id: str):
    if not merchant_id:
        return ApiErr(
            code="merchant.invalid",
            message="Missing merchant_id",
        )

    # Placeholder — real tiers come later
    return ApiOk(data=[])
