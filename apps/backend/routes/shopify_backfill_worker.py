import os
import socket
from fastapi import APIRouter, Header, HTTPException

from apps.backend.lib.supabase_admin import rpc, update_where, select_one
from apps.backend.services.shopify_backfill_service import run_backfill_slice

router = APIRouter(prefix="/shopify/backfill/worker", tags=["shopify-backfill"])

WORKER_TOKEN = os.getenv("WORKER_TOKEN", "")

@router.post("/tick")
async def backfill_worker_tick(x_worker_token: str = Header(...)):
    if not WORKER_TOKEN or x_worker_token != WORKER_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

    worker_id = socket.gethostname()

    jobs = rpc("claim_shopify_backfill_job", {"worker_id": worker_id})
    if not jobs:
        return {"ok": True, "job": None}

    job = jobs[0]

    merchant = select_one("merchants", {"id": job["merchant_id"]})
    if not merchant:
        update_where("shopify_backfill_jobs", {"id": job["id"]}, {
            "status": "failed",
            "error_last": "merchant_not_found",
        })
        return {"ok": False, "job": job["id"], "error": "merchant_not_found"}

    try:
        result = await run_backfill_slice(
            merchant_id=job["merchant_id"],
            shop_domain=job["shop_domain"],
            access_token=merchant["shopify_access_token"],
            points_per_dollar=float(merchant.get("points_per_dollar") or 1.0),
            cursor=job["last_cursor"],
        )

        patch = {
            "attempts": int(job["attempts"]) + 1,
            "stats_orders": int(job["stats_orders"]) + int(result["orders_processed"]),
            "stats_customers": int(job["stats_customers"]) + int(result["customers_touched"]),
        }

        if result["done"]:
            patch["status"] = "completed"
            patch["last_cursor"] = None
            update_where("merchants", {"id": job["merchant_id"]}, {"engine_state": "ready"})
        else:
            patch["status"] = "retrying"
            patch["last_cursor"] = result["next_cursor"]

        update_where("shopify_backfill_jobs", {"id": job["id"]}, patch)
        return {"ok": True, "job": job["id"], "done": result["done"]}

    except Exception as e:
        update_where("shopify_backfill_jobs", {"id": job["id"]}, {
            "status": "retrying",
            "attempts": int(job["attempts"]) + 1,
            "error_last": str(e),
        })
        raise
