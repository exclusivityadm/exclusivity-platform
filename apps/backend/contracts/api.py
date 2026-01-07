# apps/backend/contracts/api.py
# =====================================================
# Exclusivity Backend — STEP 20
# CONTRACT FREEZE (AUTHORITATIVE API SHAPES)
#
# This file defines the ONLY allowed response shapes
# for frontend-facing APIs.
#
# RULES (LOCKED):
# - Every endpoint returns ApiResponse[T]
# - Errors NEVER appear on success variants
# - Success NEVER appears on error variants
# - Frontend TypeScript mirrors this exactly
#
# Any future change requires a new version (v2).
# =====================================================

from __future__ import annotations
from typing import Generic, TypeVar, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

T = TypeVar("T")

# -----------------------------------------------------
# Base Response Types
# -----------------------------------------------------

class ApiOk(BaseModel, Generic[T]):
    ok: Literal[True] = True
    data: T


class ApiErr(BaseModel):
    ok: Literal[False] = False
    code: str = Field(..., description="Stable machine-readable error code")
    message: str = Field(..., description="Human-readable error")
    details: Optional[Dict[str, Any]] = None


ApiResponse = ApiOk[T] | ApiErr

# =====================================================
# MERCHANT
# =====================================================

class MerchantProfile(BaseModel):
    merchant_id: str
    shop_domain: str
    installed: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MerchantSettings(BaseModel):
    merchant_id: str
    settings: Dict[str, Any] = Field(default_factory=dict)


class MerchantTier(BaseModel):
    tier_id: str
    name: str
    threshold: int


# =====================================================
# LOYALTY
# =====================================================

class LoyaltyLedgerWrite(BaseModel):
    merchant_id: str
    customer_id: str
    delta: int
    reason: Optional[str] = None


class LoyaltyLedgerResult(BaseModel):
    ledger_id: str
    balance: int


# =====================================================
# ACTION PREVIEW (Dashboard)
# =====================================================

class ActionPreviewRequest(BaseModel):
    merchant_id: str
    action_type: str
    payload: Dict[str, Any]


class ActionPreviewResult(BaseModel):
    estimated_cost: int
    estimated_reach: int
    warnings: list[str] = Field(default_factory=list)


# =====================================================
# ONBOARDING / INSTALL
# =====================================================

class ResolveMerchantResult(BaseModel):
    merchant_id: str
    created: bool


# =====================================================
# ERROR CODES (LOCKED ENUM BY CONVENTION)
# =====================================================
#
# merchant.not_found
# merchant.not_installed
# merchant.invalid
#
# loyalty.invalid_delta
# loyalty.write_failed
#
# action.preview_failed
#
# auth.missing
# auth.invalid
# auth.expired
#
# internal.error
#
# =====================================================
