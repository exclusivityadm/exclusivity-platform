from typing import Any, Dict
from .supabase_admin import new_uuid, select_one, upsert_one, update_where

ONBOARDING_INSTALLED = "installed"
ONBOARDING_PROFILE_CONFIRMED = "profile_confirmed"
ONBOARDING_LOYALTY_CONFIGURED = "loyalty_configured"
ONBOARDING_DASHBOARD_READY = "dashboard_ready"

def upsert_merchant_from_shopify(shop_domain: str, access_token: str) -> Dict[str, Any]:
    """
    Creates or updates merchant record keyed by shop_domain.
    """
    existing = select_one("merchants", {"shop_domain": shop_domain})
    merchant_id = (existing or {}).get("id") or new_uuid()

    row = {
        "id": merchant_id,
        "shop_domain": shop_domain,
        "shopify_access_token": access_token,
        "plan": "beta",
    }
    merchant = upsert_one("merchants", row, conflict_cols="shop_domain")

    # Ensure onboarding row exists
    onboarding = select_one("merchant_onboarding", {"merchant_id": merchant_id})
    if not onboarding:
        upsert_one(
            "merchant_onboarding",
            {"merchant_id": merchant_id, "status": ONBOARDING_INSTALLED},
            conflict_cols="merchant_id"
        )

    return merchant

def set_onboarding_status(merchant_id: str, status: str) -> None:
    update_where("merchant_onboarding", {"merchant_id": merchant_id}, {"status": status})
