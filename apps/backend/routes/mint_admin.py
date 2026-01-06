import os
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException

from apps.backend.routes.services.blockchain_orchestrator_service import enqueue_mint_job

router = APIRouter(prefix="/admin/mint", tags=["admin-mint"])

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

@router.post("/enqueue")
async def admin_enqueue_mint(body: Dict[str, Any], x_admin_token: str = Header(default="")):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

    merchant_id = body.get("merchant_id")
    customer_id = body.get("customer_id")
    job_type = body.get("job_type") or "badge_issue"
    source = body.get("source") or "admin"
    source_ref = body.get("source_ref")
    payload = body.get("payload") or {}

    if not merchant_id or not customer_id:
        raise HTTPException(status_code=400, detail="missing_merchant_id_or_customer_id")

    job = enqueue_mint_job(
        merchant_id=str(merchant_id),
        customer_id=str(customer_id),
        job_type=str(job_type),
        source=str(source),
        source_ref=str(source_ref) if source_ref else None,
        payload=payload,
    )
    return {"ok": True, "job": job}
