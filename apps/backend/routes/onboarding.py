from fastapi import APIRouter
from apps.backend.services.supabase_admin import select_one, insert_one
from apps.backend.services.loyalty_service import ensure_loyalty_baseline

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status")
def onboarding_status():
    """
    Drop A source-of-truth endpoint.
    Assumes single merchant (store-installed custom app).
    """

    # 1. Resolve merchant (single-store assumption)
    merchant = select_one("merchants", {})

    if not merchant:
        return {
            "merchant_exists": False,
            "onboarding_complete": False,
            "loyalty_initialized": False,
        }

    merchant_id = merchant["id"]

    # 2. Resolve onboarding record (or default)
    onboarding = select_one(
        "merchant_onboarding",
        {"merchant_id": merchant_id}
    )

    onboarding_complete = False
    if onboarding:
        onboarding_complete = onboarding.get("status") == "complete"

    # 3. Ensure loyalty baseline exists (idempotent)
    loyalty_initialized = ensure_loyalty_baseline(merchant_id)

    return {
        "merchant_exists": True,
        "onboarding_complete": onboarding_complete,
        "loyalty_initialized": loyalty_initialized,
    }


@router.post("/complete")
def complete_onboarding():
    """
    Final Drop A action.
    Marks onboarding complete.
    """

    merchant = select_one("merchants", {})
    if not merchant:
        return {"ok": False, "error": "Merchant not found"}

    merchant_id = merchant["id"]

    existing = select_one(
        "merchant_onboarding",
        {"merchant_id": merchant_id}
    )

    if existing:
        insert_one(
            "merchant_onboarding",
            {
                "merchant_id": merchant_id,
                "status": "complete",
            },
            upsert=True,
        )
    else:
        insert_one(
            "merchant_onboarding",
            {
                "merchant_id": merchant_id,
                "status": "complete",
            }
        )

    return {"ok": True}
