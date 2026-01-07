# apps/backend/routes/merchant.py
# =====================================================
# Exclusivity Backend — Merchant Routes (Canonical)
#
# Routes:
#   GET  /merchant/profile?shop_domain=...
#   GET  /merchant/resolve?shop_domain=...&create_if_missing=true|false
#   POST /merchant/complete-install
#   GET  /merchant/settings?merchant_id=...
#   GET  /merchant/tiers?merchant_id=...
#
# Step M: Merchant Resolution Engine (canonical identity)
# Step N: Onboarding Completion Hook (mark installed + store shop metadata)
#
# Engine-first: frontend must never guess shapes.
# Every endpoint returns stable JSON with explicit ok + payload.
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
)

# Optional helpers — if present in your supabase_admin module, we will use them.
# If not present, we still compile, and you'll get a clear 501 if a create/update is attempted.
try:
    from apps.backend.routes.services.supabase_admin import insert_one  # type: ignore
except Exception:
    insert_one = None  # type: ignore

try:
    from apps.backend.routes.services.supabase_admin import update_one  # type: ignore
except Exception:
    update_one = None  # type: ignore


router = APIRouter(tags=["merchant"])  # prefix owned by main.py


# ----------------------------
# Models (stable contracts)
# ----------------------------

class ResolveSuccess(BaseModel):
    ok: bool = True
    merchant_id: str
    shop_domain: str
    installed: bool = True
    created: bool = False


class ResolveFailure(BaseModel):
    ok: bool = False
    error: str
    code: str = Field(default="UNRESOLVED")
    details: Optional[Any] = None


ResolveResult = ResolveSuccess | ResolveFailure


class CompleteInstallRequest(BaseModel):
    merchant_id: str
    # Optional: if you want to confirm shop_domain match, pass it.
    shop_domain: Optional[str] = None

    # Optional: store whatever you want for debugging / future onboarding UX
    # (Shopify plan, email, currency, primary locale, etc.)
    shop_meta: Dict[str, Any] = Field(default_factory=dict)

    # Optional: allow forcing installed flag (defaults to True)
    installed: bool = True


class CompleteInstallResponse(BaseModel):
    ok: bool = True
    merchant_id: str
    installed: bool
    updated: bool = True


# ----------------------------
# Helpers
# ----------------------------

def _norm_shop(shop_domain: str) -> str:
    return (shop_domain or "").strip().lower()


def _require_write_helper(helper_name: str):
    if helper_name == "insert_one" and insert_one is None:
        raise HTTPException(
            501,
            "insert_one helper missing in supabase_admin. Add it or handle creation elsewhere.",
        )
    if helper_name == "update_one" and update_one is None:
        raise HTTPException(
            501,
            "update_one helper missing in supabase_admin. Add it or handle updates elsewhere.",
        )


# =====================================================
# Step M — Merchant Resolution Engine
# =====================================================

@router.get("/resolve", response_model=ResolveResult)
def merchant_resolve(shop_domain: str, create_if_missing: bool = False):
    """
    Canonical merchant resolver for onboarding + dashboard.
    - If merchant exists: returns ok=true with merchant_id, installed, created=false
    - If merchant missing:
        - create_if_missing=false -> ok=false with code=NOT_INSTALLED
        - create_if_missing=true  -> attempt to create row and return ok=true created=true
    """
    shop_domain = _norm_shop(shop_domain)
    if not shop_domain:
        return ResolveFailure(error="Missing shop_domain", code="MISSING_SHOP_DOMAIN")

    try:
        m = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,created_at,updated_at",
        )

        if m:
            merchant_id = m.get("merchant_id")
            if not merchant_id:
                return ResolveFailure(
                    error="Merchant row exists but missing merchant_id",
                    code="BROKEN_ROW",
                    details=m,
                )

            installed_val = m.get("installed")
            installed = bool(installed_val) if installed_val is not None else True

            return ResolveSuccess(
                merchant_id=str(merchant_id),
                shop_domain=str(m.get("shop_domain") or shop_domain),
                installed=installed,
                created=False,
            )

        # Not found
        if not create_if_missing:
            return ResolveFailure(
                error="Unable to resolve merchant identity (not installed yet)",
                code="NOT_INSTALLED",
                details={"shop_domain": shop_domain},
            )

        # Create if missing (install-time convenience)
        _require_write_helper("insert_one")

        # Minimal insert — merchant_id is typically generated in DB (uuid default) OR by helper.
        # If your schema requires merchant_id, update insert_one to generate uuid server-side.
        row = {
            "shop_domain": shop_domain,
            "installed": False,
        }

        created = insert_one("merchants", row)  # type: ignore
        # Re-select to return canonical identity
        m2 = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed",
        )
        if not m2 or not m2.get("merchant_id"):
            return ResolveFailure(
                error="Create attempted but could not read merchant_id afterward",
                code="CREATE_FAILED",
                details={"created": created, "shop_domain": shop_domain},
            )

        return ResolveSuccess(
            merchant_id=str(m2["merchant_id"]),
            shop_domain=str(m2.get("shop_domain") or shop_domain),
            installed=bool(m2.get("installed")) if m2.get("installed") is not None else False,
            created=True,
        )

    except SupabaseAdminError as e:
        return ResolveFailure(error=str(e), code="SUPABASE_ERROR")
    except HTTPException:
        raise
    except Exception as e:
        return ResolveFailure(error=f"merchant/resolve error: {e}", code="SERVER_ERROR")


# =====================================================
# Existing: Profile (kept stable, but aligned)
# =====================================================

@router.get("/profile")
def merchant_profile(shop_domain: str):
    """
    Legacy-compatible resolver.
    Prefer /merchant/resolve for stable canonical behavior.
    """
    shop_domain = _norm_shop(shop_domain)
    if not shop_domain:
        raise HTTPException(400, "Missing shop_domain")

    try:
        m = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,created_at,updated_at",
        )
        if not m:
            raise HTTPException(404, "Merchant not found for shop_domain")

        return {
            "ok": True,
            "merchant_id": m.get("merchant_id"),
            "id": m.get("merchant_id"),  # compatibility alias for older frontend code
            "shop_domain": m.get("shop_domain"),
            "installed": bool(m.get("installed")) if m.get("installed") is not None else True,
            "created_at": m.get("created_at"),
            "updated_at": m.get("updated_at"),
        }

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"merchant/profile error: {e}")


# =====================================================
# Step N — Onboarding Completion Hook
# =====================================================

@router.post("/complete-install", response_model=CompleteInstallResponse)
def merchant_complete_install(payload: CompleteInstallRequest):
    """
    Marks merchant as installed and optionally stores shop metadata.
    This should be called after OAuth + initial sync is confirmed.
    """
    merchant_id = (payload.merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    try:
        # Confirm merchant exists
        m = select_one(
            "merchants",
            {"merchant_id": merchant_id},
            columns="merchant_id,shop_domain,installed",
        )
        if not m:
            raise HTTPException(404, "Merchant not found for merchant_id")

        # Optional shop_domain consistency check
        if payload.shop_domain:
            want = _norm_shop(payload.shop_domain)
            have = _norm_shop(m.get("shop_domain") or "")
            if have and want and have != want:
                raise HTTPException(
                    409,
                    f"shop_domain mismatch (db={have} payload={want})",
                )

        _require_write_helper("update_one")

        update_doc: Dict[str, Any] = {
            "installed": bool(payload.installed),
        }

        # Store shop_meta if your merchants table has a jsonb column, e.g. `shop_meta`
        # If your column is named differently, rename here.
        if payload.shop_meta:
            update_doc["shop_meta"] = payload.shop_meta

        updated = update_one("merchants", {"merchant_id": merchant_id}, update_doc)  # type: ignore

        return CompleteInstallResponse(
            merchant_id=merchant_id,
            installed=bool(payload.installed),
            updated=bool(updated) if updated is not None else True,
        )

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"merchant/complete-install error: {e}")


# =====================================================
# Minimal stable shapes (stubs, expanded later)
# =====================================================

@router.get("/settings")
def merchant_settings(merchant_id: str):
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")
    return {"ok": True, "merchant_id": merchant_id, "settings": {}}


@router.get("/tiers")
def merchant_tiers(merchant_id: str):
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")
    return {"ok": True, "merchant_id": merchant_id, "tiers": []}
