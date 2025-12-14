from fastapi import APIRouter
from apps.backend.services.supabase_admin import select_one

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status")
def onboarding_status():
    """
    Drop A final onboarding truth endpoint.
    Assumes single merchant (store-installed app).
    """

    merchant = select_one("merchants", {})

    if not merchant:
        return {
            "merchant_exists": False,
            "onboarding_complete": False,
            "loyalty_initialized": False,
        }

    onboarding = select_one(
        "merchant_onboarding",
        {"merchant_id": merchant["id"]}
    )

    onboarding_complete = (
        onboarding is not None and onboarding.get("status") == "complete"
    )

    return {
        "merchant_exists": True,
        "onboarding_complete": onboarding_complete,
        "loyalty_initialized": True,
    }


@router.post("/complete")
def complete_onboarding():
    """
    Drop A closure endpoint.
    Persistence deferred to Drop B.
    """
    return {"ok": True}
