# apps/backend/routes/shopify.py
from __future__ import annotations

import os
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from apps.backend.services.shopify_backfill_service import run_backfill

router = APIRouter(tags=["shopify"])

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()

def _require_admin(x_admin_token: str | None):
    if not ADMIN_TOKEN:
        # If not set, we allow (dev-only). But never crash.
        return
    if not x_admin_token or x_admin_token.strip() != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ---------------------------------------
# Existing webhook (preserved)
# ---------------------------------------
@router.post("/webhook")
async def webhook(payload: dict):
    return {"ok": True}

# ---------------------------------------
# Preserve OAuth callback if you already have it
# ---------------------------------------
try:
    from apps.backend.routes.shopify_oauth import router as oauth_router  # type: ignore
    router.include_router(oauth_router, prefix="/oauth")
except Exception:
    # If oauth router not present, we simply skip it.
    pass

# ---------------------------------------
# Backfill
# ---------------------------------------

class BackfillIn(BaseModel):
    merchant_id: str = Field(..., min_length=8)
    shop_domain: str = Field(..., description="exclusivity-dev.myshopify.com")
    access_token: str = Field(..., min_length=10)
    points_per_dollar: float = Field(default=1.0, ge=0.0, le=1000.0)

@router.post("/backfill/run")
def backfill_run(
    body: BackfillIn,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
):
    """
    Canonical end-to-end backfill:
      orders -> ledger -> balances -> tiers.
    """
    _require_admin(x_admin_token)
    return run_backfill(
        merchant_id=body.merchant_id,
        shop_domain=body.shop_domain,
        access_token=body.access_token,
        points_per_dollar=body.points_per_dollar,
    )
