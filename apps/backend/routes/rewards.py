# apps/backend/routes/rewards.py
# =====================================================
# Exclusivity Backend — Rewards Engine (Step H)
#
# Routes:
#   GET  /rewards/catalog?merchant_id=...
#   POST /rewards/catalog/seed-defaults?merchant_id=...        (worker token)
#   POST /rewards/issue?merchant_id=...                        (worker token)
#   POST /rewards/redeem?merchant_id=...                       (worker token for now)
#
# Notes:
# - Service-role only data access
# - Notification outbox is written here (Step I will send)
# =====================================================

from __future__ import annotations

import os
import json
import time
from typing import Dict, Any, Optional

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["rewards"])  # prefix owned by main.py


# -----------------------------------------------------
# Env + security
# -----------------------------------------------------

def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()

def _must_env(name: str) -> str:
    v = _env(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def require_worker_token(request: Request) -> None:
    expected = _must_env("BACKFILL_WORKER_TOKEN")
    got = (request.headers.get("X-Worker-Token") or "").strip()
    if not got or got != expected:
        raise HTTPException(401, "Invalid worker token")


# -----------------------------------------------------
# Supabase REST (service role)
# -----------------------------------------------------

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

def sb_insert_many(table: str, rows: list[Dict[str, Any]]) -> None:
    if not rows:
        return
    h = sb_headers()
    h["Prefer"] = "resolution=merge-duplicates,return=minimal"
    r = requests.post(sb_url(f"/rest/v1/{table}"), headers=h, data=json.dumps(rows), timeout=30)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase insert error: {r.text}")

def sb_insert_one(table: str, row: Dict[str, Any]) -> None:
    h = sb_headers()
    h["Prefer"] = "return=minimal"
    r = requests.post(sb_url(f"/rest/v1/{table}"), headers=h, data=json.dumps(row), timeout=30)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase insert error: {r.text}")


# -----------------------------------------------------
# Models
# -----------------------------------------------------

class IssueRewardBody(BaseModel):
    customer_ref: str = Field(..., description="Email preferred")
    reward_code: str = Field(..., description="Matches reward_catalog.reward_code")
    event_type: str = Field("reward_issued", description="Event type label")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RedeemBody(BaseModel):
    customer_ref: str
    reward_code: str
    external_ref: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------
# Helpers
# -----------------------------------------------------

def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def normalize_customer_ref(v: str) -> str:
    return (v or "").strip().lower()


# -----------------------------------------------------
# Routes
# -----------------------------------------------------

@router.get("/catalog")
def catalog(merchant_id: str):
    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    rows = sb_select(
        "reward_catalog",
        f"merchant_id=eq.{merchant_id}&select=reward_code,reward_name,reward_type,required_tier_rank,required_points,payload,is_active&order=reward_code.asc",
    )
    return {"ok": True, "merchant_id": merchant_id, "rewards": rows}


@router.post("/catalog/seed-defaults")
def seed_defaults(request: Request, merchant_id: str):
    require_worker_token(request)

    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    existing = sb_select("reward_catalog", f"merchant_id=eq.{merchant_id}&select=reward_code&limit=1")
    if existing:
        return {"ok": True, "merchant_id": merchant_id, "seeded": False, "reason": "catalog already exists"}

    defaults = [
        {
            "merchant_id": merchant_id,
            "reward_code": "WELCOME10",
            "reward_name": "Welcome Reward",
            "reward_type": "discount",
            "required_tier_rank": 1,
            "required_points": 0,
            "payload": {"label": "10% off", "hint": "Issued after onboarding"},
            "is_active": True,
        },
        {
            "merchant_id": merchant_id,
            "reward_code": "TIER_UP",
            "reward_name": "Tier Upgrade Reward",
            "reward_type": "perk",
            "required_tier_rank": 2,
            "required_points": 0,
            "payload": {"label": "Perk", "hint": "Issued on tier upgrade"},
            "is_active": True,
        },
    ]

    sb_insert_many("reward_catalog", defaults)
    return {"ok": True, "merchant_id": merchant_id, "seeded": True, "count": len(defaults)}


@router.post("/issue")
def issue_reward(request: Request, merchant_id: str, body: IssueRewardBody):
    require_worker_token(request)

    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    customer_ref = normalize_customer_ref(body.customer_ref)
    if not customer_ref:
        raise HTTPException(400, "Missing customer_ref")

    # Validate reward exists + active
    reward = sb_select(
        "reward_catalog",
        f"merchant_id=eq.{merchant_id}&reward_code=eq.{body.reward_code}&select=reward_code,is_active,required_tier_rank,required_points&limit=1",
    )
    if not reward:
        raise HTTPException(404, "Unknown reward_code")
    if not bool(reward[0].get("is_active")):
        raise HTTPException(400, "Reward is not active")

    # Snapshot current member state if present
    member = sb_select(
        "loyalty_members",
        f"merchant_id=eq.{merchant_id}&customer_ref=eq.{customer_ref}&select=points_total,tier_rank,tier_name&limit=1",
    )
    snap_points = int(member[0].get("points_total") or 0) if member else None
    snap_rank = int(member[0].get("tier_rank") or 1) if member else None
    snap_name = str(member[0].get("tier_name") or "Tier 1") if member else None

    # Create reward event
    sb_insert_one("reward_events", {
        "merchant_id": merchant_id,
        "customer_ref": customer_ref,
        "event_type": body.event_type,
        "reward_code": body.reward_code,
        "points_snapshot": snap_points,
        "tier_rank_snapshot": snap_rank,
        "tier_name_snapshot": snap_name,
        "metadata": body.metadata or {},
    })

    # Queue notification (Step I will send)
    sb_insert_one("notification_outbox", {
        "merchant_id": merchant_id,
        "customer_ref": customer_ref,
        "channel": "internal",
        "template_key": "reward_issued",
        "payload": {
            "reward_code": body.reward_code,
            "event_type": body.event_type,
            "points_snapshot": snap_points,
            "tier_rank_snapshot": snap_rank,
            "tier_name_snapshot": snap_name,
            "meta": body.metadata or {},
        },
        "status": "queued",
        "attempts": 0,
        "updated_at": now_iso(),
    })

    return {"ok": True, "merchant_id": merchant_id, "customer_ref": customer_ref, "reward_code": body.reward_code}


@router.post("/redeem")
def redeem_reward(request: Request, merchant_id: str, body: RedeemBody):
    """
    For now: worker-only. Later (Step J) we'll support authenticated merchant app sessions.
    """
    require_worker_token(request)

    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    customer_ref = normalize_customer_ref(body.customer_ref)
    if not customer_ref:
        raise HTTPException(400, "Missing customer_ref")

    if not (body.reward_code or "").strip():
        raise HTTPException(400, "Missing reward_code")

    sb_insert_one("reward_redemptions", {
        "merchant_id": merchant_id,
        "customer_ref": customer_ref,
        "reward_code": body.reward_code,
        "status": "claimed",
        "external_ref": body.external_ref,
        "metadata": body.metadata or {},
        "updated_at": now_iso(),
    })

    sb_insert_one("reward_events", {
        "merchant_id": merchant_id,
        "customer_ref": customer_ref,
        "event_type": "reward_redeemed",
        "reward_code": body.reward_code,
        "metadata": {"external_ref": body.external_ref, **(body.metadata or {})},
    })

    sb_insert_one("notification_outbox", {
        "merchant_id": merchant_id,
        "customer_ref": customer_ref,
        "channel": "internal",
        "template_key": "reward_redeemed",
        "payload": {"reward_code": body.reward_code, "external_ref": body.external_ref},
        "status": "queued",
        "attempts": 0,
        "updated_at": now_iso(),
    })

    return {"ok": True, "merchant_id": merchant_id, "customer_ref": customer_ref, "reward_code": body.reward_code}
