# apps/backend/routes/shopify_backfill_worker.py
# =====================================================
# Exclusivity Backend — Shopify Backfill Worker
#
# INTERNAL USE ONLY
# - Claims queued Shopify backfill jobs
# - Runs under service role
# - Never exposed to frontend clients
#
# Route:
#   POST /shopify/backfill/claim
# =====================================================

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    rpc,
)

router = APIRouter(tags=["shopify-backfill-worker"])


@router.post("/shopify/backfill/claim")
def claim_backfill_job(dry_run: bool = False):
    """
    Claim the next available Shopify backfill job.

    - Uses Supabase RPC: claim_shopify_backfill_job
    - Locks job to this worker
    - dry_run allows visibility without mutation
    """

    try:
        result = rpc(
            "claim_shopify_backfill_job",
            {
                "dry_run": bool(dry_run),
            },
        )

        if not result:
            return {
                "ok": True,
                "job": None,
                "message": "No backfill jobs available",
            }

        return {
            "ok": True,
            "job": result,
        }

    except SupabaseAdminError as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"shopify backfill worker error: {e}",
        )
