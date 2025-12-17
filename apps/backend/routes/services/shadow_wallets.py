import os
from typing import Any, Dict, Optional, List
from supabase import create_client, Client


def _sb() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def get_active_merchant_id() -> str:
    """
    Drop B assumes single merchant context (like Drop A).
    """
    sb = _sb()
    res = sb.table("merchants").select("id").limit(1).execute()
    data = res.data or []
    if not data:
        raise RuntimeError("No merchant found in merchants table")
    return data[0]["id"]


def get_or_create_wallet(merchant_id: str, customer_ref: str) -> Dict[str, Any]:
    sb = _sb()

    existing = (
        sb.table("customer_wallets")
        .select("*")
        .eq("merchant_id", merchant_id)
        .eq("customer_ref", customer_ref)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    created = (
        sb.table("customer_wallets")
        .insert({"merchant_id": merchant_id, "customer_ref": customer_ref})
        .execute()
    )
    if not created.data:
        raise RuntimeError("Failed to create wallet")
    return created.data[0]


def post_ledger_event(
    merchant_id: str,
    wallet_id: str,
    event_id: str,
    delta: int,
    reason: Optional[str] = None,
    source: str = "api",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Idempotent by (merchant_id, event_id) unique constraint.
    If it already exists, we return the existing record.
    """
    if delta == 0:
        raise ValueError("delta must be non-zero")

    sb = _sb()

    # Check if event already exists (idempotency)
    existing = (
        sb.table("wallet_ledger")
        .select("*")
        .eq("merchant_id", merchant_id)
        .eq("event_id", event_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        return {"ok": True, "idempotent": True, "ledger": existing.data[0]}

    payload = {
        "merchant_id": merchant_id,
        "wallet_id": wallet_id,
        "event_id": event_id,
        "delta": int(delta),
        "reason": reason,
        "source": source,
        "metadata": metadata or {},
    }

    inserted = sb.table("wallet_ledger").insert(payload).execute()
    if not inserted.data:
        raise RuntimeError("Failed to insert ledger event")

    return {"ok": True, "idempotent": False, "ledger": inserted.data[0]}


def get_balance(merchant_id: str, wallet_id: str) -> int:
    sb = _sb()
    res = (
        sb.table("wallet_balances")
        .select("balance")
        .eq("merchant_id", merchant_id)
        .eq("wallet_id", wallet_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return 0
    return int(res.data[0]["balance"])


def get_ledger(merchant_id: str, wallet_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    sb = _sb()
    res = (
        sb.table("wallet_ledger")
        .select("*")
        .eq("merchant_id", merchant_id)
        .eq("wallet_id", wallet_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []
