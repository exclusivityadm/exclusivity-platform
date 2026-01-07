# apps/backend/routes/loyalty.py
# =====================================================
# Exclusivity Backend — Loyalty Engine (Step F)
#
# Purpose:
# - Convert Shopify orders into loyalty ledger entries
# - Deterministic, idempotent, backend-only
#
# Routes:
#   POST /loyalty/award-from-orders?merchant_id=...
#
# Security:
# - Service role only
# - Worker token required
# =====================================================

from __future__ import annotations

import os
import time
import json
from typing import Dict, Any, Optional

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


# -----------------------------------------------------
# Loyalty math (simple + deterministic)
# -----------------------------------------------------

def calculate_points(order_payload: Dict[str, Any]) -> int:
    """
    Canonical rule (v1):
    - 1 point per whole currency unit of order total
    - Excludes refunds (handled later)
    """
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
# Main award route
# -----------------------------------------------------

@router.post("/award-from-orders")
async def award_from_orders(
    request: Request,
    merchant_id: str,
    limit: int = 100,
):
    """
    Process Shopify orders → loyalty ledger.
    Safe to run repeatedly (idempotent).
    """
    require_worker_token(request)

    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    limit = max(1, min(limit, 500))

    # -------------------------------------------------
    # Load orders
    # -------------------------------------------------
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

        # Idempotency enforced by unique index
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
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
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
