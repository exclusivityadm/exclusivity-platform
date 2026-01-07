# apps/backend/routes/notifications.py
# =====================================================
# Exclusivity Backend — Notification Outbox (Step H)
#
# Routes:
#   POST /notify/flush?limit=...          (worker token)
#   GET  /notify/outbox?status=queued...  (worker token)
#
# Step I will implement real providers (Postmark/Klaviyo/SMS).
# For now this just advances state so the system is end-to-end testable.
# =====================================================

from __future__ import annotations

import os
import json
import time
from typing import Dict, Any, Optional

import requests
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["notify"])  # prefix owned by main.py


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()

def _must_env(name: str) -> str:
    v = _env(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def require_worker_token(request: Request) -> None:
    expected = _must_env("BACKFILL_WORKER_TOKEN")
    got = (request.headers.get("X-Worker-Token") or "").strip()
    if not got or got != expected:
        raise HTTPException(401, "Invalid worker token")


# Supabase REST
def sb_headers() -> Dict[str, str]:
    key = _must_env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def sb_url(path: str) -> str:
    return _must_env("SUPABASE_URL").rstrip("/") + path

def sb_select(table: str, qs: str) -> list[dict]:
    r = requests.get(sb_url(f"/rest/v1/{table}?{qs}"), headers=sb_headers(), timeout=30)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase select error: {r.text}")
    return r.json()

def sb_patch(table: str, match_qs: str, patch: Dict[str, Any]) -> None:
    r = requests.patch(
        sb_url(f"/rest/v1/{table}?{match_qs}"),
        headers=sb_headers(),
        data=json.dumps(patch),
        timeout=30,
    )
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase patch error: {r.text}")


@router.get("/outbox")
def list_outbox(request: Request, status: str = "queued", limit: int = 50):
    require_worker_token(request)
    limit = max(1, min(limit, 200))
    rows = sb_select(
        "notification_outbox",
        f"status=eq.{status}&select=outbox_id,merchant_id,customer_ref,channel,template_key,payload,status,attempts,created_at,updated_at&order=created_at.asc&limit={limit}",
    )
    return {"ok": True, "status": status, "count": len(rows), "rows": rows}


@router.post("/flush")
def flush_outbox(request: Request, limit: int = 50):
    """
    Placeholder sender:
    - marks queued messages as 'sent'
    - increments attempts
    Step I will replace this with real provider dispatch per channel.
    """
    require_worker_token(request)
    limit = max(1, min(limit, 200))

    queued = sb_select(
        "notification_outbox",
        f"status=eq.queued&select=outbox_id,attempts&order=created_at.asc&limit={limit}",
    )

    sent = 0
    for msg in queued:
        outbox_id = msg.get("outbox_id")
        attempts = int(msg.get("attempts") or 0) + 1
        if not outbox_id:
            continue
        sb_patch(
            "notification_outbox",
            f"outbox_id=eq.{outbox_id}",
            {"status": "sent", "attempts": attempts, "updated_at": now_iso(), "last_error": None},
        )
        sent += 1

    return {"ok": True, "processed": len(queued), "marked_sent": sent}
