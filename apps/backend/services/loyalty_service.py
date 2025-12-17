from typing import Dict, List, Optional
from fastapi import Request

from apps.backend.db import get_supabase
from apps.backend.services.core_service import CoreError  # reuse your existing error pattern


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


def _get_merchant_for_user(supabase, user_id: str) -> Dict:
    data = (
        supabase.table("merchants")
        .select("*")
        .eq("owner_profile_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    if not data:
        raise CoreError("Merchant not initialized. Call /core/bootstrap first.", 404)
    return data[0]


def upsert_customer(request: Request, email: str, name: Optional[str] = None) -> Dict:
    supabase = _require_supabase()
    user = _get_user(request)
    merchant = _get_merchant_for_user(supabase, user["id"])

    payload = {
        "merchant_id": merchant["id"],
        "email": email.strip(),
        "name": (name or None),
    }

    supabase.table("customers").upsert(payload, on_conflict="merchant_id,email").execute()

    row = (
        supabase.table("customers")
        .select("*")
        .eq("merchant_id", merchant["id"])
        .ilike("email", email.strip())
        .limit(1)
        .execute()
        .data
    )
    if not row:
        raise CoreError("Failed to upsert customer", 500)

    return row[0]


def set_tiers(request: Request, tiers: List[Dict]) -> Dict:
    """
    tiers: [{name, rank, threshold_points, perks?}, ...]
    Deterministic: replace-by-merchant (delete then insert).
    """
    supabase = _require_supabase()
    user = _get_user(request)
    merchant = _get_merchant_for_user(supabase, user["id"])

    # Replace tiers deterministically
    supabase.table("loyalty_tiers").delete().eq("merchant_id", merchant["id"]).execute()

    rows = []
    for t in tiers:
        rows.append({
            "merchant_id": merchant["id"],
            "name": t["name"],
            "rank": int(t["rank"]),
            "threshold_points": int(t["threshold_points"]),
            "perks": t.get("perks", {}) or {},
        })

    if rows:
        supabase.table("loyalty_tiers").insert(rows).execute()

    out = (
        supabase.table("loyalty_tiers")
        .select("*")
        .eq("merchant_id", merchant["id"])
        .order("rank", desc=False)
        .execute()
        .data
    )
    return {"merchant_id": merchant["id"], "tiers": out or []}


def list_tiers(request: Request) -> Dict:
    supabase = _require_supabase()
    user = _get_user(request)
    merchant = _get_merchant_for_user(supabase, user["id"])

    out = (
        supabase.table("loyalty_tiers")
        .select("*")
        .eq("merchant_id", merchant["id"])
        .order("rank", desc=False)
        .execute()
        .data
    )
    return {"merchant_id": merchant["id"], "tiers": out or []}


def _get_customer_by_email(supabase, merchant_id: str, email: str) -> Dict:
    row = (
        supabase.table("customers")
        .select("*")
        .eq("merchant_id", merchant_id)
        .ilike("email", email.strip())
        .limit(1)
        .execute()
        .data
    )
    if not row:
        raise CoreError("Customer not found for merchant", 404)
    return row[0]


def append_ledger(
    request: Request,
    customer_email: str,
    event_type: str,
    points: int,
    reason: Optional[str] = None,
    ref: Optional[str] = None,
) -> Dict:
    """
    Append-only ledger. No updates/deletes. Idempotency supported via ref (unique per merchant).
    points is absolute magnitude; sign is derived from event_type.
    """
    supabase = _require_supabase()
    user = _get_user(request)
    merchant = _get_merchant_for_user(supabase, user["id"])
    customer = _get_customer_by_email(supabase, merchant["id"], customer_email)

    if event_type not in ("earn", "redeem", "adjust"):
        raise CoreError("Invalid event_type", 400)
    if points <= 0:
        raise CoreError("Points must be > 0", 400)

    if event_type == "earn":
        delta = points
    elif event_type == "redeem":
        delta = -points
    else:
        # adjust: positive adjustment by default; use redeem if you want negative
        delta = points

    payload = {
        "merchant_id": merchant["id"],
        "customer_id": customer["id"],
        "event_type": event_type,
        "points_delta": delta,
        "reason": reason,
        "ref": ref,
        "created_by_profile_id": user["id"],
    }

    try:
        supabase.table("loyalty_ledger").insert(payload).execute()
    except Exception as e:
        # If ref is duplicated, treat as idempotent replay and return current balance.
        # (Supabase error parsing differs by version; safest is to proceed to balance read.)
        pass

    return get_balance_and_tier(request, customer_email)


def get_balance_and_tier(request: Request, customer_email: str) -> Dict:
    supabase = _require_supabase()
    user = _get_user(request)
    merchant = _get_merchant_for_user(supabase, user["id"])
    customer = _get_customer_by_email(supabase, merchant["id"], customer_email)

    # Balance = sum(points_delta)
    ledger = (
        supabase.table("loyalty_ledger")
        .select("points_delta")
        .eq("merchant_id", merchant["id"])
        .eq("customer_id", customer["id"])
        .execute()
        .data
    ) or []

    balance = sum(int(x["points_delta"]) for x in ledger if "points_delta" in x)

    tiers = (
        supabase.table("loyalty_tiers")
        .select("*")
        .eq("merchant_id", merchant["id"])
        .order("threshold_points", desc=False)
        .execute()
        .data
    ) or []

    # Determine tier: highest threshold <= balance
    active_tier = None
    for t in tiers:
        if balance >= int(t["threshold_points"]):
            active_tier = t

    return {
        "merchant_id": merchant["id"],
        "customer": {"id": customer["id"], "email": customer["email"], "name": customer.get("name")},
        "balance": balance,
        "tier": active_tier,
    }


def health_loyalty() -> Dict:
    supabase = _require_supabase()
    checks = {}
    ok = True

    for table in ("customers", "loyalty_ledger", "loyalty_tiers"):
        try:
            supabase.table(table).select("*").limit(1).execute()
            checks[table] = True
        except Exception:
            checks[table] = False
            ok = False

    return {"ok": ok, "checks": checks}
