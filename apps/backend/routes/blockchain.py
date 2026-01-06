import os
from fastapi import APIRouter, Header, HTTPException

from apps.backend.routes.services.blockchain_orchestrator_service import process_one_mint_job

router = APIRouter(prefix="/blockchain", tags=["blockchain"])

WORKER_TOKEN = os.getenv("WORKER_TOKEN", "")

@router.get("/status")
async def blockchain_status():
    # Abstracted status for internal monitoring
    return {"ok": True, "mode": os.getenv("BLOCKCHAIN_MODE", "internal")}

@router.post("/worker/tick")
async def blockchain_worker_tick(x_worker_token: str = Header(...)):
    if not WORKER_TOKEN or x_worker_token != WORKER_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")
    return process_one_mint_job()
