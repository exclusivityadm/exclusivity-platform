from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any

from apps.backend.services.daily_briefing import build_daily_briefing
from apps.backend.services.action_router import preview_action, execute_action
from apps.backend.services.monetize.entitlements import get_plan_for_merchant, can_execute_actions

# Keep router prefix-free; main.py mounts /ai
router = APIRouter(tags=["ai"])


@router.get("/daily-briefing")
async def daily_briefing(merchant_id: str, persona: str = "orion"):
    res = build_daily_briefing(merchant_id=merchant_id, persona=persona)
    if not res.get("ok"):
        raise HTTPException(500, res.get("error") or "Failed to build briefing")
    return JSONResponse(content=res, status_code=200)


class ActionIn(BaseModel):
    merchant_id: str
    action: Dict[str, Any]


@router.post("/action/preview")
async def action_preview(payload: ActionIn):
    return JSONResponse(content=preview_action(payload.action), status_code=200)


@router.post("/action/execute")
async def action_execute(payload: ActionIn):
    plan = get_plan_for_merchant(payload.merchant_id)
    if not can_execute_actions(plan):
        return JSONResponse(
            content={
                "ok": False,
                "status_code": 403,
                "plan": plan,
                "message": "Preview tier cannot execute actions. Upgrade to enable execution.",
            },
            status_code=403,
        )

    return JSONResponse(content=execute_action(payload.action), status_code=200)
