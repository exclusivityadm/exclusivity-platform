# apps/backend/services/action_ledger.py
from __future__ import annotations

from typing import Any, Dict, Optional
import uuid
import time

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    insert_one,
    update_one,
    select_one,
)


def now_ms() -> int:
    return int(time.time() * 1000)


def create_preview(
    *,
    merchant_id: str,
    request_id: str,
    action_type: str,
    input_payload: Dict[str, Any],
    cost_estimate: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    preview_id = str(uuid.uuid4())

    row = {
        "preview_id": preview_id,
        "merchant_id": merchant_id,
        "request_id": request_id,
        "action_type": action_type,
        "input": input_payload,
        "cost_estimate": cost_estimate or {},
        "status": "PREVIEW",
        "created_at_ms": now_ms(),
    }

    insert_one("action_previews", row)
    return row


def mark_preview_executed(preview_id: str, execution_id: str) -> None:
    update_one("action_previews", {"preview_id": preview_id}, {"status": "EXECUTED", "execution_id": execution_id})


def write_ledger_event(
    *,
    merchant_id: str,
    request_id: str,
    actor_type: str,
    actor_id: str | None,
    action_type: str,
    phase: str,  # PREVIEW | EXECUTE | RESULT | ERROR
    preview_id: str | None = None,
    execution_id: str | None = None,
    payload: Dict[str, Any] | None = None,
) -> str:
    event_id = str(uuid.uuid4())
    row = {
        "event_id": event_id,
        "merchant_id": merchant_id,
        "request_id": request_id,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "action_type": action_type,
        "phase": phase,
        "preview_id": preview_id,
        "execution_id": execution_id,
        "payload": payload or {},
        "created_at_ms": now_ms(),
    }
    insert_one("action_ledger", row)
    return event_id


def get_preview(preview_id: str) -> Dict[str, Any] | None:
    return select_one("action_previews", {"preview_id": preview_id}, columns="*")
