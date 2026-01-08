# apps/backend/services/monetize/entitlements.py
# =====================================================
# Monetization + Entitlements (Canonical)
#
# Rules (LOCKED):
# - "preview" plan is FREE and has NO execution.
# - All paid plans can execute, but capabilities are tier-gated.
# - Capability gating must be enforced server-side.
# =====================================================

from __future__ import annotations

import os
import json
import time
from typing import Any, Dict, Optional, Tuple

import requests

# -----------------------------
# Plan + capability model
# -----------------------------

PLAN_PREVIEW = "preview"
PLAN_GOLD = "gold"
PLAN_PLATINUM = "platinum"
PLAN_BLACK_LABEL = "black_label"

PAID_PLANS = {PLAN_GOLD, PLAN_PLATINUM, PLAN_BLACK_LABEL}

# Capability levels:
# 0 = none
# 1 = basic
# 2 = advanced
# 3 = elite
CAPS: Dict[str, Dict[str, int]] = {
    PLAN_PREVIEW: {
        "execute_actions": 0,
        "marketing_send": 0,
        "pricing_apply": 0,
        "loyalty_worker": 0,
        "shopify_backfill": 0,
        "ai_automation": 0,
    },
    PLAN_GOLD: {
        "execute_actions": 1,
        "marketing_send": 1,
        "pricing_apply": 1,
        "loyalty_worker": 1,
        "shopify_backfill": 1,
        "ai_automation": 1,
    },
    PLAN_PLATINUM: {
        "execute_actions": 2,
        "marketing_send": 2,
        "pricing_apply": 2,
        "loyalty_worker": 2,
        "shopify_backfill": 2,
        "ai_automation": 2,
    },
    PLAN_BLACK_LABEL: {
        "execute_actions": 3,
        "marketing_send": 3,
        "pricing_apply": 3,
        "loyalty_worker": 3,
        "shopify_backfill": 3,
        "ai_automation": 3,
    },
}

# -----------------------------
# Supabase minimal client (service role)
# -----------------------------

def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()

def _must_env(name: str) -> str:
    v = _env(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def _sb_headers() -> Dict[str, str]:
    key = _must_env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _sb_url(path: str) -> str:
    return _must_env("SUPABASE_URL").rstrip("/") + path

def _sb_select_one(table: str, qs: str) -> Optional[dict]:
    r = requests.get(_sb_url(f"/rest/v1/{table}?{qs}&limit=1"), headers=_sb_headers(), timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Supabase select error: {r.text}")
    data = r.json()
    return data[0] if isinstance(data, list) and data else None

# -----------------------------
# Merchant plan lookup
# -----------------------------

def _normalize_plan(p: Optional[str]) -> str:
    p = (p or "").strip().lower()
    if p in ("blacklabel", "black-label", "black label"):
        return PLAN_BLACK_LABEL
    if p in ("black_label",):
        return PLAN_BLACK_LABEL
    if p in ("platinum",):
        return PLAN_PLATINUM
    if p in ("gold",):
        return PLAN_GOLD
    if p in ("preview", "free"):
        return PLAN_PREVIEW
    # unknown -> default
    return _env("DEFAULT_PLAN", PLAN_PREVIEW).strip().lower() or PLAN_PREVIEW

def get_plan_for_merchant(merchant_id: str) -> str:
    """
    Canonical plan resolver.
    Prefers DB value if present, otherwise DEFAULT_PLAN env, otherwise preview.
    Expected column (recommended): merchants.plan
    """
    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        return PLAN_PREVIEW

    # Allow disabling DB lookup in emergencies
    if _env("DISABLE_PLAN_DB_LOOKUP", "false").lower() == "true":
        return _normalize_plan(_env("DEFAULT_PLAN", PLAN_PREVIEW))

    try:
        row = _sb_select_one("merchants", f"merchant_id=eq.{merchant_id}&select=merchant_id,plan")
        if row and row.get("plan") is not None:
            return _normalize_plan(str(row.get("plan")))
    except Exception:
        # Fail closed to preview if DB is unreachable
        return PLAN_PREVIEW

    return _normalize_plan(_env("DEFAULT_PLAN", PLAN_PREVIEW))

# -----------------------------
# Capability checks
# -----------------------------

def cap_level(plan: str, cap: str) -> int:
    plan = _normalize_plan(plan)
    return int(CAPS.get(plan, CAPS[PLAN_PREVIEW]).get(cap, 0))

def is_paid(plan: str) -> bool:
    return _normalize_plan(plan) in PAID_PLANS

def can_execute_actions(plan: str) -> bool:
    # Preview cannot execute anything
    return cap_level(plan, "execute_actions") >= 1

def require_cap(plan: str, cap: str, level: int = 1) -> Tuple[bool, str]:
    """
    Returns (allowed, reason)
    """
    plan_n = _normalize_plan(plan)
    have = cap_level(plan_n, cap)
    if have >= level:
        return True, ""
    if plan_n == PLAN_PREVIEW:
        return False, f"Preview plan cannot execute '{cap}'. Upgrade to enable execution."
    return False, f"Plan '{plan_n}' lacks required capability '{cap}' level {level} (have {have})."
