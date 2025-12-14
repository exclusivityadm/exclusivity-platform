from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.backend.repositories.loyalty_repository import (
    LoyaltyRepository,
    create_supabase_client_from_env,
)
from apps.backend.services.loyalty.loyalty_service import LoyaltyService


router = APIRouter(prefix="/loyalty", tags=["loyalty"])


# -----------------------------
# Dependency wiring (minimal)
# Replace with your canonical DI later
# -----------------------------
def get_loyalty_repo() -> LoyaltyRepository:
    sb = create_supabase_client_from_env()
    return LoyaltyRepository(sb)


def get_loyalty_service(
    repo: LoyaltyRepository = Depends(get_loyalty_repo),
) -> LoyaltyService:
    return LoyaltyService(repo)


# -----------------------------
# Schemas
# -----------------------------
class PolicyUpsertRequest(BaseModel):
    policy: Dict[str, Any] = Field(default_factory=dict)


class PolicyResponse(BaseModel):
    policy: Dict[str, Any]


class MemberStatusResponse(BaseModel):
    status: Dict[str, Any]


class OrderLineIn(BaseModel):
    line_id: str
    product_id: Optional[str] = None
    title: str = "Item"
    unit_price: Decimal = Decimal("0.00")
    quantity: int = 1
    eligible_for_points: bool = True


class AwardOrderRequest(BaseModel):
    merchant_id: str
    order_id: str
    member_ref: str
    currency: str = "USD"
    discounts_total: Decimal = Decimal("0.00")
    lines: List[OrderLineIn] = Field(default_factory=list)

    # Optional explicit lifetime spend increment (recommended to reflect actual paid amount)
    lifetime_spend_increment: Optional[Decimal] = None


class RefundAdjustRequest(BaseModel):
    merchant_id: str
    order_id: str
    refund_id: str
    member_ref: str

    # Mapping: line_id -> refunded eligible amount (currency)
    refund_line_amounts: Dict[str, Decimal] = Field(default_factory=dict)

    # Lifetime spend is lifetime by default; this stays False unless explicitly chosen
    decrement_lifetime_spend: bool = False


# -----------------------------
# Routes
# -----------------------------
@router.get("/policy/{merchant_id}", response_model=PolicyResponse)
async def get_policy(
    merchant_id: str,
    svc: LoyaltyService = Depends(get_loyalty_service),
) -> PolicyResponse:
    policy = await svc.get_policy(merchant_id)
    return PolicyResponse(policy=policy.to_dict())


@router.put("/policy/{merchant_id}", response_model=PolicyResponse)
async def put_policy(
    merchant_id: str,
    payload: PolicyUpsertRequest,
    svc: LoyaltyService = Depends(get_loyalty_service),
) -> PolicyResponse:
    policy = await svc.upsert_policy(merchant_id, payload.policy)
    return PolicyResponse(policy=policy.to_dict())


@router.get(
    "/member/{merchant_id}/{member_ref}/status",
    response_model=MemberStatusResponse,
)
async def member_status(
    merchant_id: str,
    member_ref: str,
    svc: LoyaltyService = Depends(get_loyalty_service),
) -> MemberStatusResponse:
    status = await svc.get_member_status(merchant_id, member_ref)
    return MemberStatusResponse(status=status.to_dict())


@router.post("/order/award")
async def award_order(
    payload: AwardOrderRequest,
    svc: LoyaltyService = Depends(get_loyalty_service),
) -> Dict[str, Any]:
    if not payload.lines:
        raise HTTPException(status_code=400, detail="Order must include at least one line")

    result = await svc.award_for_order(
        merchant_id=payload.merchant_id,
        order_id=payload.order_id,
        member_ref=payload.member_ref,
        lines=[x.model_dump() for x in payload.lines],
        discounts_total=payload.discounts_total,
        currency=payload.currency,
        lifetime_spend_increment=payload.lifetime_spend_increment,
        event_id_prefix="earn",
        idempotency_prefix="idem:earn",
    )
    return result


@router.post("/order/refund")
async def refund_adjust(
    payload: RefundAdjustRequest,
    svc: LoyaltyService = Depends(get_loyalty_service),
) -> Dict[str, Any]:
    if not payload.refund_line_amounts:
        raise HTTPException(
            status_code=400,
            detail="refund_line_amounts cannot be empty",
        )

    result = await svc.adjust_for_refund(
        merchant_id=payload.merchant_id,
        order_id=payload.order_id,
        refund_id=payload.refund_id,
        member_ref=payload.member_ref,
        refund_line_amounts=payload.refund_line_amounts,
        decrement_lifetime_spend=payload.decrement_lifetime_spend,
        event_id_prefix="refund",
        idempotency_prefix="idem:refund",
    )
    return result
