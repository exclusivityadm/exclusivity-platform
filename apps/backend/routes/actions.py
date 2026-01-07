# apps/backend/routes/actions.py

from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()


def ok(data: Any) -> Dict[str, Any]:
    return {"ok": True, "data": data}


def err(message: str, details: Any = None) -> Dict[str, Any]:
    payload = {"ok": False, "error": message}
    if details:
        payload["details"] = details
    return payload


@router.post("/actions/preview")
async def preview_action(payload: Dict[str, Any]):
    """
    Non-mutating preview.
    No writes. No side effects.
    """
    try:
        return ok({
            "estimated_cost": 0,
            "estimated_reach": 0,
            "warnings": []
        })
    except Exception as e:
        return err("Preview failed", str(e))


@router.post("/actions/run")
async def run_action(payload: Dict[str, Any]):
    """
    Executes an action.
    """
    try:
        return ok({
            "action_id": "placeholder",
            "status": "queued"
        })
    except Exception as e:
        return err("Action execution failed", str(e))
