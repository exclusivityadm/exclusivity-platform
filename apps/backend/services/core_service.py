from typing import Dict
from fastapi import Request

from apps.backend.db import get_supabase

ONBOARDING_STATES = ["created", "identity_verified", "store_connected", "ready"]


class CoreError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _require_supabase():
    supabase = get_supabase()
    if not supabase:
        raise CoreError("Supabase client unavailable", 500)
    return supabase


def _get_user(request: Request) -> Dict[str, str]:
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise CoreError("Missing or invalid Authorization header", 401)

    token = auth.split(" ", 1)[1]
    supabase = _require_supabase()

    try:
        res = supabase.auth.get_user(token)
        user = res.user
    except Exception:
        raise CoreError("Invalid or expired token", 401)

    if not user or not user.id or not user.email:
        raise CoreError("Unable to resolve user identity", 401)

    return {"id": user.id, "email": user.email}


def bootstrap(request: Request):
    supabase = _require_supabase()
    user = _get_user(request)

    # profile
    supabase.table("profiles").upsert({
        "id": user["id"],
        "email": user["email"],
    }).execute()

    # merchant
    merchant = (
        supabase.table("merchants")
        .select("*")
        .eq("owner_profile_id", user["id"])
        .limit(1)
        .execute()
        .data
    )

    if not merchant:
        merchant = (
            supabase.table("merchants")
            .insert({
                "owner_profile_id": user["id"],
                "status": "active",
            })
            .execute()
            .data
        )

    merchant = merchant[0]

    # onboarding
    supabase.table("merchant_onboarding").upsert({
        "merchant_id": merchant["id"],
        "state": "created",
    }).execute()

    onboarding = (
        supabase.table("merchant_onboarding")
        .select("*")
        .eq("merchant_id", merchant["id"])
        .limit(1)
        .execute()
        .data
    )

    return {
        "profile": user,
        "merchant": merchant,
        "onboarding": onboarding[0] if onboarding else None,
    }


def me(request: Request):
    supabase = _require_supabase()
    user = _get_user(request)

    merchant = (
        supabase.table("merchants")
        .select("*")
        .eq("owner_profile_id", user["id"])
        .limit(1)
        .execute()
        .data
    )

    onboarding = None
    if merchant:
        onboarding = (
            supabase.table("merchant_onboarding")
            .select("*")
            .eq("merchant_id", merchant[0]["id"])
            .limit(1)
            .execute()
            .data
        )

    return {
        "profile": user,
        "merchant": merchant[0] if merchant else None,
        "onboarding": onboarding[0] if onboarding else None,
    }


def advance_onboarding(request: Request):
    supabase = _require_supabase()
    user = _get_user(request)

    merchant = (
        supabase.table("merchants")
        .select("*")
        .eq("owner_profile_id", user["id"])
        .limit(1)
        .execute()
        .data
    )

    if not merchant:
        raise CoreError("Merchant not initialized", 404)

    merchant = merchant[0]

    onboarding = (
        supabase.table("merchant_onboarding")
        .select("*")
        .eq("merchant_id", merchant["id"])
        .limit(1)
        .execute()
        .data
    )

    if not onboarding:
        raise CoreError("Onboarding record missing", 500)

    onboarding = onboarding[0]
    state = onboarding["state"]

    if state == "ready":
        return onboarding

    idx = ONBOARDING_STATES.index(state)
    next_state = ONBOARDING_STATES[idx + 1]

    supabase.table("merchant_onboarding").update({
        "state": next_state
    }).eq("merchant_id", merchant["id"]).execute()

    return {
        "merchant_id": merchant["id"],
        "state": next_state,
    }


def health_core():
    supabase = _require_supabase()
    checks = {}

    for table in ("profiles", "merchants", "merchant_onboarding"):
        try:
            supabase.table(table).select("*").limit(1).execute()
            checks[table] = True
        except Exception:
            checks[table] = False

    return {
        "ok": all(checks.values()),
        "checks": checks,
    }
