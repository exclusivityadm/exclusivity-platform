# apps/backend/routes/shopify_backfill_worker.py
# =====================================================
# Exclusivity Backend — Shopify Backfill Worker (Internal)
#
# Route:
#   POST /shopify/backfill/claim
#
# Response shape standardized:
#   { ok: true, data: {...} }
#   { ok: false, error: "...", details?: ... }
# =====================================================

from fastapi import APIRouter, HTTPException
from apps.backend.routes.services.supabase_admin import rpc, SupabaseAdminError
from apps.backend.routes.services.api_result import ok, err

router = APIRouter(tags=["shopify-backfill-worker"])


@router.post("/shopify/backfill/claim")
def claim_shopify_backfill_job(dry_run: bool = False):
    try:
        job = rpc("claim_shopify_backfill_job", {"dry_run": bool(dry_run)})

        if not job:
            return ok({"job": None, "message": "No backfill jobs available"})

        return ok({"job": job})

    except SupabaseAdminError as e:
        # Still return 500 for operational visibility
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"shopify backfill worker error: {e}")
