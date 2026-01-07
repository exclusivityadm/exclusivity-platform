# apps/backend/routes/merchant_install.py
# =====================================================
# Exclusivity Backend — Merchant Install Finalization
#
# Route:
#   POST /merchant/install/complete
#
# Responsibilities:
# - Idempotent install completion
# - Canonical source of "installed = true"
# - Safe for retries
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime, timezone

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
    update_one,
)

router = APIRouter(tags=["merchant"])


@router.post("/merchant/install/complete")
def complete_install(payload: Dict[str, Any]):
    """
    Finalize merchant installation.

    Required:
      - merchant_id (UUID)

    Idempotent:
      - If already installed, returns success.
    """

    merchant_id = (payload.get("merchant_id") or "").strip()

    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    try:
        merchant = select_one(
            "merchants",
            {"merchant_id": merchant_id},
            columns="merchant_id,installed",
        )

        if not merchant:
            raise HTTPException(404, "Merchant not found")

        # Idempotent success
        if merchant.get("installed") is True:
            return {
                "ok": True,
                "merchant_id": merchant_id,
                "installed": True,
                "already_installed": True,
            }

        update_one(
            "merchants",
            {"merchant_id": merchant_id},
            {
                "installed": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "ok": True,
            "merchant_id": merchant_id,
            "installed": True,
            "already_installed": False,
        }

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"install/complete error: {e}")
