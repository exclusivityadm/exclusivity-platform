from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from apps.backend.services.supabase_admin import select_one
from apps.backend.services.loyalty_service import (
    ensure_loyalty_baseline,
    loyalty_snapshot,
    issue_points,
    get_customer_points,
    calculate_tier,
)

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _resolve_merchant_id(merchant_id: Optional[str] = None) -> str:
    """
    Drop A assumption: single merchant.
    Future-proof: allow explicit merchant_id when multi-tenant arrives.
    """
    if merchant_id:
        return merchant_id

    merchant = select_one("merchants", {})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found.")
    return merchant["id"]


# ---------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------

class IssuePointsRequest(BaseModel):
    merchant_id: Optional[str] = Field(default=None, description="Optional for single-merchant mode.")
    customer_id: str
    amount: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=200)


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------

@router.get("/bootstrap")
def bootstrap_loyalty(merchant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Idempotent initializer.
    Keeps compatibility with existing deployments that call /loyalty/bootstrap.
    """
    mid = _resolve_merchant_id(merchant_id)
    ok = ensure_loyalty_baseline(mid)
    return {"ok": ok, "merchant_id": mid, "snapshot": loyalty_snapshot(mid)}


@router.get("/snapshot")
def get_snapshot(merchant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    System-level snapshot (tiers, max supply, issued supply, etc).
    Used by onboarding, dashboard, AI.
    """
    mid = _resolve_merchant_id(merchant_id)
    return {"ok": True, "merchant_id": mid, "snapshot": loyalty_snapshot(mid)}


@router.get("/customer/points")
def customer_points(customer_id: str, merchant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns current customer point balance.
    """
    mid = _resolve_merchant_id(merchant_id)
    pts = get_customer_points(mid, customer_id)
    return {"ok": True, "merchant_id": mid, "customer_id": customer_id, "points": pts}


@router.get("/customer/tier")
def customer_tier(customer_id: str, merchant_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns deterministic tier evaluation for a customer.
    """
    mid = _resolve_merchant_id(merchant_id)
    result = calculate_tier(mid, customer_id)
    return {"ok": True, "merchant_id": mid, "customer_id": customer_id, **result}


@router.post("/issue")
def issue(req: IssuePointsRequest) -> Dict[str, Any]:
    """
    Issues points (server-controlled).
    Note: Auth/permissions will be enforced later; route exists now for completeness/testing.
    """
    mid = _resolve_merchant_id(req.merchant_id)

    try:
        result = issue_points(
            merchant_id=mid,
            customer_id=req.customer_id,
            amount=req.amount,
            reason=req.reason,
        )
        # Return updated customer context too (useful for UI + AI)
        pts = get_customer_points(mid, req.customer_id)
        tier = calculate_tier(mid, req.customer_id)
        return {
            "ok": True,
            "merchant_id": mid,
            "customer_id": req.customer_id,
            "result": result,
            "customer_points": pts,
            "customer_tier": tier.get("tier"),
            "next_tier_at": tier.get("next_tier_at"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
