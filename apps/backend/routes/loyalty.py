from fastapi import APIRouter, HTTPException
from apps.backend.services.supabase_admin import select_one, upsert_one
from apps.backend.services.merchant_service import (
    ONBOARDING_LOYALTY_CONFIGURED,
    set_onboarding_status
)

router = APIRouter(prefix="/loyalty", tags=["loyalty"])

@router.post("/bootstrap")
def bootstrap_loyalty(merchant_id: str):
    merchant = select_one("merchants", {"id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found.")

    # Baseline loyalty config (merchant-editable later in Drop D)
    existing = select_one("loyalty_config", {"merchant_id": merchant_id})
    if not existing:
        config = upsert_one(
            "loyalty_config",
            {
                "merchant_id": merchant_id,
                "points_label": "Points",
                "earn_rate": 1.0,  # 1 point per $1
                "currency": "USD",
                "enabled": True
            },
            conflict_cols="merchant_id"
        )

        # Baseline tiers
        upsert_one(
            "loyalty_tiers",
            {"merchant_id": merchant_id, "tier": "Member", "threshold": 0},
            conflict_cols="merchant_id,tier"
        )
        upsert_one(
            "loyalty_tiers",
            {"merchant_id": merchant_id, "tier": "VIP", "threshold": 500},
            conflict_cols="merchant_id,tier"
        )
    else:
        config = existing

    set_onboarding_status(merchant_id, ONBOARDING_LOYALTY_CONFIGURED)
    return {"ok": True, "merchant_id": merchant_id, "config": config}
