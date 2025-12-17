from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os

from apps.backend.services.monetize.entitlements import resolve_merchant_entitlements
from apps.backend.services.monetize.repository import assign_plan

router = APIRouter(prefix="/monetize", tags=["monetize"])

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()

class AssignPlanIn(BaseModel):
    merchant_id: str
    plan_key: str  # preview | gold | platinum | black_label

@router.get("/merchant/{merchant_id}")
def get_merchant_plan(merchant_id: str):
    return JSONResponse(content=resolve_merchant_entitlements(merchant_id))

@router.post("/assign")
def admin_assign_plan(payload: AssignPlanIn, x_admin_token: str | None = Header(default=None)):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=501, detail="ADMIN_TOKEN not configured on server.")
    if not x_admin_token or x_admin_token.strip() != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized (missing/invalid X-Admin-Token).")

    out = assign_plan(payload.merchant_id, payload.plan_key)
    # return the resolved state after assignment
    return JSONResponse(content=resolve_merchant_entitlements(payload.merchant_id))
