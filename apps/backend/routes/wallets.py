from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from apps.backend.services.shadow_wallets import (
    get_active_merchant_id,
    get_or_create_wallet,
    post_ledger_event,
    get_balance,
    get_ledger,
)

router = APIRouter(prefix="/wallets", tags=["wallets"])


class WalletMutation(BaseModel):
    customer_ref: str = Field(..., description="Shopify customer id/email/reference")
    points: int = Field(..., gt=0, description="Positive integer points")
    event_id: str = Field(..., description="Idempotency key (unique per merchant)")
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("/balance")
def wallet_balance(customer_ref: str):
    merchant_id = get_active_merchant_id()
    wallet = get_or_create_wallet(merchant_id, customer_ref)
    balance = get_balance(merchant_id, wallet["id"])
    return {"ok": True, "customer_ref": customer_ref, "wallet_id": wallet["id"], "balance": balance}


@router.get("/ledger")
def wallet_ledger(customer_ref: str, limit: int = 50):
    merchant_id = get_active_merchant_id()
    wallet = get_or_create_wallet(merchant_id, customer_ref)
    rows = get_ledger(merchant_id, wallet["id"], limit=limit)
    return {"ok": True, "customer_ref": customer_ref, "wallet_id": wallet["id"], "ledger": rows}


@router.post("/credit")
def wallet_credit(body: WalletMutation):
    merchant_id = get_active_merchant_id()
    wallet = get_or_create_wallet(merchant_id, body.customer_ref)

    result = post_ledger_event(
        merchant_id=merchant_id,
        wallet_id=wallet["id"],
        event_id=body.event_id,
        delta=body.points,
        reason=body.reason,
        source="api",
        metadata=body.metadata or {},
    )
    balance = get_balance(merchant_id, wallet["id"])
    return {"ok": True, "result": result, "balance": balance}


@router.post("/debit")
def wallet_debit(body: WalletMutation):
    merchant_id = get_active_merchant_id()
    wallet = get_or_create_wallet(merchant_id, body.customer_ref)

    # optional: prevent negative balances in beta
    current = get_balance(merchant_id, wallet["id"])
    if current - body.points < 0:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    result = post_ledger_event(
        merchant_id=merchant_id,
        wallet_id=wallet["id"],
        event_id=body.event_id,
        delta=-body.points,
        reason=body.reason,
        source="api",
        metadata=body.metadata or {},
    )
    balance = get_balance(merchant_id, wallet["id"])
    return {"ok": True, "result": result, "balance": balance}
