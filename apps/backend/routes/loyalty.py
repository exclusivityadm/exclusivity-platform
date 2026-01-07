# apps/backend/routes/loyalty.py
# =====================================================
# Exclusivity Backend — Loyalty Engine (Step F + Step G)
#
# Routes:
#   POST /loyalty/award-from-orders?merchant_id=...&limit=...
#   POST /loyalty/evaluate-tiers?merchant_id=...&limit=...
#
# Security:
# - Service role only
# - Worker token required
# =====================================================

from __future__ import annotations

import os
import time
import json
from typing import Dict, Any, Optional, Tuple

import requests
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["loyalty"])  # prefix owned by main.py


# -----------------------------------------------------
# Env helpers
# -----------------------------------------------------

def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()

def _must_env(name: str) -> str:
    v = _env(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


# -----------------------------------------------------
# Worker security
# -----------------------------------------------------

def require_worker_token(request: Request) -> None:
    expected = _must_env("BACKFILL_WORKER_TOKEN")
    got = (request.headers.get("X-Worker-Token") or "").strip()
    if not got or got != expected:
        raise HTTPException(401, "Invalid worker token")


# -----------------------------------------------------
# Supabase (service role only)
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

def sb_insert(table: str, row: Dict[str, Any]) -> None:
    h = sb_headers()
    h["Prefer"] = "return=minimal"
    r = requests.post(
        sb_url(f"/rest/v1/{table}"),
        headers=h,
        data=json.dumps(row),
        timeout=30,
    )
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase insert error: {r.text}")

def sb_upsert_many(table: str, rows: list[Dict[str, Any]]) -> None:
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
        raise HTTPException(500, f"Supabase upsert error: {r.text}")


# -----------------------------------------------------
# Loyalty math (v1 deterministic)
# -----------------------------------------------------

def calculate_points(order_payload: Dict[str, Any]) -> int:
    try:
        total = float(order_payload.get("total_price") or 0)
    except Exception:
        total = 0.0
    return max(0, int(total))

def customer_ref_from_order(order: Dict[str, Any]) -> Optional[str]:
    email = (order.get("email") or "").strip().lower()
    if email:
        return email
    cust = order.get("customer") or {}
    cid = cust.get("id")
    return str(cid) if cid else None


# -----------------------------------------------------
# Step F — Award from orders (idempotent via unique index)
# -----------------------------------------------------

@router.post("/award-from-orders")
async def award_from_orders(request: Request, merchant_id: str, limit: int = 100):
    require_worker_token(request)

    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    limit = max(1, min(limit, 500))

    orders = sb_select(
        "shopify_orders",
        f"merchant_id=eq.{merchant_id}&select=order_id,payload&limit={limit}&order=updated_at.asc",
    )

    awarded = 0
    skipped = 0

    for row in orders:
        order_id = row.get("order_id")
        payload = row.get("payload") or {}

        if not order_id:
            skipped += 1
            continue

        points = calculate_points(payload)
        if points <= 0:
            skipped += 1
            continue

        ledger_row = {
            "merchant_id": merchant_id,
            "source_type": "shopify_order",
            "source_id": str(order_id),
            "customer_ref": customer_ref_from_order(payload),
            "points_awarded": points,
            "metadata": {
                "order_name": payload.get("name"),
                "currency": payload.get("currency"),
                "total_price": payload.get("total_price"),
            },
        }

        try:
            sb_insert("loyalty_ledger", ledger_row)
            awarded += 1
        except HTTPException as e:
            # Duplicate = already awarded
            msg = str(e).lower()
            if "duplicate" in msg or "unique" in msg:
                skipped += 1
                continue
            raise

    return {
        "ok": True,
        "merchant_id": merchant_id,
        "processed": len(orders),
        "awarded": awarded,
        "skipped": skipped,
    }


# -----------------------------------------------------
# Step G — Evaluate tiers from ledger totals
# -----------------------------------------------------

def pick_tier(points_total: int, tiers: list[dict]) -> Tuple[int, str]:
    """
    tiers: list sorted ascending by tier_rank with threshold_points
    chooses the highest tier whose threshold_points <= points_total
    """
    chosen_rank = 1
    chosen_name = "Tier 1"
    for t in tiers:
        thr = int(t.get("threshold_points") or 0)
        rank = int(t.get("tier_rank") or 1)
        name = str(t.get("tier_name") or f"Tier {rank}")
        if points_total >= thr:
            chosen_rank, chosen_name = rank, name
    return chosen_rank, chosen_name


@router.post("/evaluate-tiers")
async def evaluate_tiers(request: Request, merchant_id: str, limit: int = 500):
    """
    Roll up ledger totals per customer_ref and upsert loyalty_members.
    Safe to run repeatedly.
    """
    require_worker_token(request)

    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    limit = max(1, min(limit, 2000))

    tiers = sb_select(
        "loyalty_tiers",
        f"merchant_id=eq.{merchant_id}&select=tier_rank,tier_name,threshold_points&order=tier_rank.asc",
    )

    # If tiers not seeded yet, force an explicit message (keeps things deterministic)
    if not tiers:
        return {
            "ok": False,
            "merchant_id": merchant_id,
            "error": "No tiers found. Run POST /merchant/tiers/seed-defaults first.",
        }

    # Pull ledger rows that have a customer_ref
    ledger_rows = sb_select(
        "loyalty_ledger",
        f"merchant_id=eq.{merchant_id}&select=customer_ref,points_awarded&customer_ref=not.is.null&limit={limit}",
    )

    # Aggregate totals
    totals: Dict[str, int] = {}
    for r in ledger_rows:
        cref = (r.get("customer_ref") or "").strip().lower()
        if not cref:
            continue
        pts = int(r.get("points_awarded") or 0)
        totals[cref] = totals.get(cref, 0) + pts

    # Upsert members
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    upserts: list[Dict[str, Any]] = []

    for cref, points_total in totals.items():
        rank, name = pick_tier(points_total, tiers)
        upserts.append({
            "merchant_id": merchant_id,
            "customer_ref": cref,
            "points_total": points_total,
            "tier_rank": rank,
            "tier_name": name,
            "last_source": "ledger_rollup",
            "last_evaluated_at": now_iso,
            "updated_at": now_iso,
        })

    sb_upsert_many("loyalty_members", upserts)

    return {
        "ok": True,
        "merchant_id": merchant_id,
        "ledger_rows_considered": len(ledger_rows),
        "members_upserted": len(upserts),
    }
