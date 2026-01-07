# apps/backend/routes/shopify_webhooks.py
# =====================================================
# Exclusivity Backend — Shopify Webhooks (Minimal)
#
# Handles:
#   - app/uninstalled
#
# Notes:
# - No HMAC verification yet (Step 19)
# - Ingest-only, idempotent-safe
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, timezone

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
    update_one,
)

router = APIRouter(tags=["shopify"])


@router.post("/shopify/webhooks/app_uninstalled")
async def shopify_app_uninstalled(request: Request):
    """
    Shopify webhook: app/uninstalled
    """

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")

    shop_domain = (payload.get("myshopify_domain") or "").strip().lower()

    if not shop_domain:
        raise HTTPException(400, "Missing myshopify_domain")

    try:
        merchant = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,installed",
        )

        # If merchant does not exist, webhook is still considered successful
        if not merchant:
            return {"ok": True, "ignored": True}

        # Idempotent uninstall
        if merchant.get("installed") is False:
            return {
                "ok": True,
                "merchant_id": merchant["merchant_id"],
                "already_uninstalled": True,
            }

        update_one(
            "merchants",
            {"merchant_id": merchant["merchant_id"]},
            {
                "installed": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "ok": True,
            "merchant_id": merchant["merchant_id"],
            "already_uninstalled": False,
        }

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"shopify/app_uninstalled error: {e}")
