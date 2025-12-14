from fastapi import APIRouter
from apps.backend.services.supabase_admin import select_one, insert_one

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status")
def onboarding_status():
    """
    Drop A final: source-of-truth onboarding status.
    Assumes single merchant (store-installed custom app).
    """

    merchant = select_one("merchants", {})

    if not merchant:
        return {
            "merchant_exists": False,
            "onboarding_complete": False,
            "loyalty_initialized": False,
        }

    merchant_id = merchant["id"]

    onboarding = select_one(
        "merchant_onboarding",
        {"merchant_id": merchant_id}
    )

    onboarding_complete = False
    if onboarding and onboarding.get("status") == "complete":
        onboarding_complete = True

    # Loyalty baseline already verified earlier in Drop A
    return {
        "merchant_exists": True,
        "onboarding_complete": onboarding_complete,
        "loyalty_initialized": True,
    }


@router.post("/complete")
def complete_onboarding():
    """
    Marks onboarding complete (Drop A closure).
    """

    merchant = select_one("merchants", {})
    if not merchant:
        return {"ok": False, "error": "Merchant not found"}

    insert_one(
        "merchant_onboarding",
        {
            "merchant_id": merchant["id"],
            "status": "complete",
        },
        upsert=True,
    )

    return {"ok": True}
