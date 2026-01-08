# apps/backend/routes/actions.py
from __future__ import annotations

from fastapi import APIRouter, Request
from typing import Any, Dict, Optional
import uuid

from apps.backend.services.action_ledger import (
    create_preview,
    write_ledger_event,
    get_preview,
    mark_preview_executed,
)

router = APIRouter(tags=["actions"])  # prefix owned by main.py


def ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, **data}


def fail(message: str, code: str = "ERROR", details: Any | None = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "message": message, "code": code}
    if details is not None:
        out["details"] = details
    return out


@router.post("/preview")
async def preview(request: Request, body: Dict[str, Any]):
    """
    Body:
      {
        "action_type": "AI_CAMPAIGN" | "LOYALTY_REWARD" | ...
        "input": {...},
        "cost_estimate": {... optional ...}
      }
    """
    ctx = getattr(request.state, "ctx", None)
    if not ctx or not ctx.merchant_id:
        return fail("Unable to resolve merchant identity", code="MERCHANT_ID_REQUIRED")

    if ctx.kill_switches.global_pause:
        return fail("System paused", code="GLOBAL_PAUSE")
    if ctx.kill_switches.ai_pause and str(body.get("action_type", "")).startswith("AI_"):
        return fail("AI paused", code="AI_PAUSE")
    if ctx.kill_switches.loyalty_pause and str(body.get("action_type", "")).startswith("LOYALTY_"):
        return fail("Loyalty paused", code="LOYALTY_PAUSE")

    action_type = str(body.get("action_type") or "").strip().upper()
    if not action_type:
        return fail("Missing action_type", code="MISSING_ACTION_TYPE")

    input_payload = body.get("input") or {}
    cost_estimate = body.get("cost_estimate") or {}

    p = create_preview(
        merchant_id=ctx.merchant_id,
        request_id=ctx.request_id,
        action_type=action_type,
        input_payload=input_payload,
        cost_estimate=cost_estimate,
    )

    write_ledger_event(
        merchant_id=ctx.merchant_id,
        request_id=ctx.request_id,
        actor_type=ctx.actor_type,
        actor_id=ctx.actor_id,
        action_type=action_type,
        phase="PREVIEW",
        preview_id=p["preview_id"],
        payload={"input": input_payload, "cost_estimate": cost_estimate},
    )

    return ok({"preview_id": p["preview_id"], "action_type": action_type, "cost_estimate": cost_estimate})


@router.post("/execute")
async def execute(request: Request, body: Dict[str, Any]):
    """
    Body:
      {
        "preview_id": "...",
        "confirm": true
      }

    NOTE:
      Drop C wires the enforcement + ledger.
      The actual underlying execution handlers (AI/Loyalty/Shopify) are called via your existing routes/services.
      This endpoint is the single canonical gate.
    """
    ctx = getattr(request.state, "ctx", None)
    if not ctx or not ctx.merchant_id:
        return fail("Unable to resolve merchant identity", code="MERCHANT_ID_REQUIRED")

    if ctx.kill_switches.global_pause:
        return fail("System paused", code="GLOBAL_PAUSE")

    preview_id = str(body.get("preview_id") or "").strip()
    if not preview_id:
        return fail("Missing preview_id", code="MISSING_PREVIEW_ID")
    if body.get("confirm") is not True:
        return fail("Missing confirm=true", code="CONFIRM_REQUIRED")

    p = get_preview(preview_id)
    if not p:
        return fail("Preview not found", code="PREVIEW_NOT_FOUND")
    if p.get("merchant_id") != ctx.merchant_id:
        return fail("Preview does not belong to merchant", code="PREVIEW_MISMATCH")

    if p.get("status") == "EXECUTED":
        # idempotent safe return
        return ok(
            {
                "execution_id": p.get("execution_id"),
                "preview_id": preview_id,
                "action_type": p.get("action_type"),
                "status": "EXECUTED",
            }
        )

    action_type = str(p.get("action_type") or "").upper()
    execution_id = str(uuid.uuid4())

    write_ledger_event(
        merchant_id=ctx.merchant_id,
        request_id=ctx.request_id,
        actor_type=ctx.actor_type,
        actor_id=ctx.actor_id,
        action_type=action_type,
        phase="EXECUTE",
        preview_id=preview_id,
        execution_id=execution_id,
        payload={"input": p.get("input") or {}, "cost_estimate": p.get("cost_estimate") or {}},
    )

    # Drop C canonical behavior:
    # We mark executed at the gate, and downstream handlers record RESULT/ERROR ledger entries.
    mark_preview_executed(preview_id, execution_id)

    return ok(
        {
            "execution_id": execution_id,
            "preview_id": preview_id,
            "action_type": action_type,
            "status": "EXECUTED",
        }
    )
