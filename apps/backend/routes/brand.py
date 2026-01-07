# apps/backend/routes/brand.py
# =====================================================
# Exclusivity Backend — Brand / Install Status
#
# Purpose:
# - Provide a single canonical readiness + install status
# - Used immediately after /merchant/resolve
#
# Routes:
#   GET /brand/status?merchant_id=...
#
# This file is INTENTIONALLY SIMPLE.
# No patching. No side effects. No mutation.
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
)

router = APIRouter(tags=["brand"])  # prefix owned by main.py


@router.get("/status")
def brand_status(merchant_id: str) -> Dict[str, Any]:
    """
    Canonical install + readiness status for a merchant.

    Returns:
      {
        ok: true,
        merchant_id: "...",
        installed: bool,
        brand_ready: bool,
        missing: [ ... ]
      }
    """

    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    try:
        merchant = select_one(
            "merchants",
            {"merchant_id": merchant_id},
            columns="merchant_id,installed",
        )

        if not merchant:
            return {"ok": False, "error": "Merchant not found"}

        brand = select_one(
            "brands",
            {"merchant_id": merchant_id},
            columns="brand_id,name,primary_color,logo_url",
        )

        missing = []

        if not brand:
            missing.append("brand_record")
        else:
            if not brand.get("name"):
                missing.append("brand_name")
            if not brand.get("primary_color"):
                missing.append("brand_primary_color")
            if not brand.get("logo_url"):
                missing.append("brand_logo")

        brand_ready = len(missing) == 0

        return {
            "ok": True,
            "merchant_id": merchant_id,
            "installed": bool(merchant.get("installed")),
            "brand_ready": brand_ready,
            "missing": missing,
        }

    except SupabaseAdminError as e:
        return {"ok": False, "error": f"Supabase error: {str(e)}"}
    except Exception as e:
        return {"ok": False, "error": f"brand/status error: {e}"}
