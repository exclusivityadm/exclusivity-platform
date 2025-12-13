from fastapi import APIRouter, HTTPException
from apps.backend.services.supabase_admin import select_one
from apps.backend.services.merchant_service import (
    ONBOARDING_INSTALLED,
    ONBOARDING_PROFILE_CONFIRMED,
    ONBOARDING_LOYALTY_CONFIGURED,
    ONBOARDING_DASHBOARD_READY,
    set_onboarding_status
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

@router.get("/status")
def onboarding_status(merchant_id: str):
    merchant = select_one("merchants", {"id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found.")
    ob = select_one("merchant_onboarding", {"merchant_id": merchant_id}) or {"status": ONBOARDING_INSTALLED}
    return {
        "merchant_id": merchant_id,
        "shop_domain": merchant.get("shop_domain"),
        "status": ob.get("status", ONBOARDING_INSTALLED),
    }

@router.post("/confirm-profile")
def confirm_profile(merchant_id: str):
    # For Drop A, profile confirmation is a simple step gate.
    set_onboarding_status(merchant_id, ONBOARDING_PROFILE_CONFIRMED)
    return {"ok": True, "status": ONBOARDING_PROFILE_CONFIRMED}

@router.post("/mark-ready")
def mark_ready(merchant_id: str):
    set_onboarding_status(merchant_id, ONBOARDING_DASHBOARD_READY)
    return {"ok": True, "status": ONBOARDING_DASHBOARD_READY}
