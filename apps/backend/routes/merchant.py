# apps/backend/routes/merchant.py
# =====================================================
# Exclusivity Backend — Merchant Routes (Step G)
#
# Routes:
#   GET  /merchant/profile?shop_domain=...
#   GET  /merchant/settings?merchant_id=...
#   GET  /merchant/tiers?merchant_id=...
#   POST /merchant/tiers/seed-defaults?merchant_id=...
#
# Notes:
# - Service-role only access to tiers for now
# - Worker token required for seeding defaults
# =====================================================

from __future__ import annotations

import os
import json
from typing import Dict, Any, Optional

import requests
from fastapi import APIRouter, HTTPException, Request

from apps.backend.routes.services.supabase_admin import (
    SupabaseAdminError,
    select_one,
)

router = APIRouter(tags=["merchant"])  # prefix owned by main.py


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
    r = requests.get(
        sb_url(f"/rest/v1/{table}?{qs}"),
        headers=sb_headers(),
        timeout=30,
    )
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase select error: {r.text}")
    return r.json()

def sb_insert_many(table: str, rows: list[Dict[str, Any]]) -> None:
    if not rows:
        return
    h = sb_headers()
    h["Prefer"] = "resolution=merge-duplicates,return=minimal"
    r = requests.post(
        sb_url(f"/rest/v1/{table}"),
        headers=h,
        data=json.dumps(rows),
        timeout=30,
    )
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase insert error: {r.text}")


# -----------------------------------------------------
# Merchant profile (existing)
# -----------------------------------------------------

@router.get("/profile")
def merchant_profile(shop_domain: str):
    shop_domain = (shop_domain or "").strip().lower()
    if not shop_domain:
        raise HTTPException(400, "Missing shop_domain")

    try:
        m = select_one(
            "merchants",
            {"shop_domain": shop_domain},
            columns="merchant_id,shop_domain,installed,created_at,updated_at",
        )
        if not m:
            raise HTTPException(404, "Merchant not found for shop_domain")

        return {
            "ok": True,
            "merchant_id": m.get("merchant_id"),
            "shop_domain": m.get("shop_domain"),
            "installed": bool(m.get("installed")) if m.get("installed") is not None else True,
            "created_at": m.get("created_at"),
            "updated_at": m.get("updated_at"),
        }

    except SupabaseAdminError as e:
        raise HTTPException(500, str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"merchant/profile error: {e}")


@router.get("/settings")
def merchant_settings(merchant_id: str):
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")
    return {"ok": True, "merchant_id": merchant_id, "settings": {}}


# -----------------------------------------------------
# Tiers (Step G)
# -----------------------------------------------------

@router.get("/tiers")
def merchant_tiers(merchant_id: str):
    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    tiers = sb_select(
        "loyalty_tiers",
        f"merchant_id=eq.{merchant_id}&select=tier_rank,tier_name,threshold_points,benefits&order=tier_rank.asc",
    )

    return {"ok": True, "merchant_id": merchant_id, "tiers": tiers}


@router.post("/tiers/seed-defaults")
def seed_default_tiers(request: Request, merchant_id: str):
    """
    Creates default tiers IF none exist. Safe to call repeatedly.
    """
    require_worker_token(request)

    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    existing = sb_select(
        "loyalty_tiers",
        f"merchant_id=eq.{merchant_id}&select=tier_rank&limit=1",
    )
    if existing:
        return {"ok": True, "merchant_id": merchant_id, "seeded": False, "reason": "tiers already exist"}

    defaults = [
        {"merchant_id": merchant_id, "tier_rank": 1, "tier_name": "Tier 1", "threshold_points": 0, "benefits": {}},
        {"merchant_id": merchant_id, "tier_rank": 2, "tier_name": "Tier 2", "threshold_points": 250, "benefits": {}},
        {"merchant_id": merchant_id, "tier_rank": 3, "tier_name": "Tier 3", "threshold_points": 500, "benefits": {}},
        {"merchant_id": merchant_id, "tier_rank": 4, "tier_name": "Tier 4", "threshold_points": 1000, "benefits": {}},
    ]

    sb_insert_many("loyalty_tiers", defaults)

    return {"ok": True, "merchant_id": merchant_id, "seeded": True, "count": len(defaults)}
