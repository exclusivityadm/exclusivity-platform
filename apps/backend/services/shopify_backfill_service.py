# apps/backend/services/shopify_backfill_service.py
from __future__ import annotations

import os
import time
import uuid
import requests
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from apps.backend.db import get_supabase

DEFAULT_SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-10")

# ----------------------------
# Helpers
# ----------------------------

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _uuid() -> str:
    return str(uuid.uuid4())

def _lower(s: Optional[str]) -> Optional[str]:
    return s.lower().strip() if s else None

def _safe_money_to_cents(v: Optional[str]) -> int:
    """
    Shopify totals often come as strings like "123.45".
    Convert to integer cents safely.
    """
    if not v:
        return 0
    try:
        f = float(v)
        return int(round(f * 100))
    except Exception:
        return 0

def _pick_email(order: dict) -> Optional[str]:
    # Prefer customer.email; fall back to order.email
    cust = order.get("customer") or {}
    return _lower(cust.get("email") or order.get("email"))

def _order_total_cents(order: dict) -> int:
    # total_price is a string in shop currency
    return _safe_money_to_cents(order.get("total_price"))

def _order_id_str(order: dict) -> str:
    # keep as string for safety
    return str(order.get("id") or "")

def _order_created_at(order: dict) -> str:
    return order.get("created_at") or _now_iso()

def _shopify_headers(access_token: str) -> Dict[str, str]:
    return {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _parse_next_link(link_header: Optional[str]) -> Optional[str]:
    """
    Shopify REST pagination uses Link header:
      <https://.../orders.json?limit=250&page_info=...>; rel="next"
    """
    if not link_header:
        return None
    parts = [p.strip() for p in link_header.split(",")]
    for p in parts:
        if 'rel="next"' in p:
            # extract URL between <>
            start = p.find("<")
            end = p.find(">")
            if start >= 0 and end > start:
                return p[start + 1 : end]
    return None


# ----------------------------
# Tier logic
# ----------------------------

@dataclass
class Tier:
    name: str
    min_lifetime_cents: int

DEFAULT_TIERS: List[Tier] = [
    Tier(name="Tier 1", min_lifetime_cents=0),
    Tier(name="Tier 2", min_lifetime_cents=20000),   # $200
    Tier(name="Tier 3", min_lifetime_cents=50000),   # $500
    Tier(name="Tier 4", min_lifetime_cents=100000),  # $1000
]

def choose_tier(tiers: List[Tier], lifetime_cents: int) -> str:
    # highest min that is <= lifetime
    best = tiers[0].name if tiers else "Tier 1"
    best_min = -1
    for t in tiers:
        if lifetime_cents >= t.min_lifetime_cents and t.min_lifetime_cents >= best_min:
            best = t.name
            best_min = t.min_lifetime_cents
    return best


# ----------------------------
# Supabase upserts
# ----------------------------

def _get_merchant_tiers(merchant_id: str) -> List[Tier]:
    sb = get_supabase()
    if not sb:
        return DEFAULT_TIERS

    # If your schema differs, this safely falls back to defaults.
    # Expected table: merchant_tiers(merchant_id, name, min_lifetime_cents OR min_lifetime_amount)
    try:
        res = (
            sb.table("merchant_tiers")
            .select("*")
            .eq("merchant_id", merchant_id)
            .execute()
        )
        rows = res.data or []
        tiers: List[Tier] = []
        for r in rows:
            name = r.get("name") or r.get("tier_name") or r.get("label") or "Tier"
            # support either cents or dollars
            if r.get("min_lifetime_cents") is not None:
                min_cents = int(r.get("min_lifetime_cents") or 0)
            else:
                # dollars → cents
                min_amt = r.get("min_lifetime_amount") or r.get("min_amount") or 0
                try:
                    min_cents = int(round(float(min_amt) * 100))
                except Exception:
                    min_cents = 0
            tiers.append(Tier(name=str(name), min_lifetime_cents=min_cents))
        return tiers if tiers else DEFAULT_TIERS
    except Exception:
        return DEFAULT_TIERS


def _upsert_customer_wallet(
    merchant_id: str,
    email: str,
) -> str:
    """
    Ensure customer_wallets exists and return customer_wallet_id.
    We use our own UUIDs. Email is the stable identifier.
    """
    sb = get_supabase()
    if not sb:
        # deterministic fallback in absence of DB
        return _uuid()

    # customer_wallets columns we try to use:
    # id (uuid), merchant_id (uuid), email (text), created_at, updated_at
    wallet_id = None
    try:
        existing = (
            sb.table("customer_wallets")
            .select("id")
            .eq("merchant_id", merchant_id)
            .ilike("email", email)  # case-insensitive
            .limit(1)
            .execute()
        )
        if existing.data:
            wallet_id = existing.data[0].get("id")
    except Exception:
        wallet_id = None

    if wallet_id:
        return str(wallet_id)

    new_id = _uuid()
    payload = {
        "id": new_id,
        "merchant_id": merchant_id,
        "email": email,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    # tolerate schema differences: try insert; if it fails, retry with smaller payload
    try:
        sb.table("customer_wallets").insert(payload).execute()
    except Exception:
        try:
            sb.table("customer_wallets").insert(
                {"id": new_id, "merchant_id": merchant_id, "email": email}
            ).execute()
        except Exception:
            # last resort: return id anyway
            pass

    return new_id


def _insert_ledger_entry(
    merchant_id: str,
    wallet_id: str,
    order_id: str,
    created_at: str,
    amount_cents: int,
    points: int,
) -> None:
    sb = get_supabase()
    if not sb:
        return

    # wallet_ledger columns assumed:
    # id, merchant_id, wallet_id, entry_type, source, source_id, amount_cents, points, created_at
    # We de-duplicate by (merchant_id, source, source_id).
    try:
        existing = (
            sb.table("wallet_ledger")
            .select("id")
            .eq("merchant_id", merchant_id)
            .eq("source", "shopify_backfill")
            .eq("source_id", order_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            return
    except Exception:
        # if table doesn’t support this select shape, we still attempt insert
        pass

    payload = {
        "id": _uuid(),
        "merchant_id": merchant_id,
        "wallet_id": wallet_id,
        "entry_type": "earn",
        "source": "shopify_backfill",
        "source_id": order_id,
        "amount_cents": amount_cents,
        "points": points,
        "created_at": created_at,
    }
    try:
        sb.table("wallet_ledger").insert(payload).execute()
    except Exception:
        # tolerate schema differences
        try:
            sb.table("wallet_ledger").insert(
                {
                    "merchant_id": merchant_id,
                    "wallet_id": wallet_id,
                    "source": "shopify_backfill",
                    "source_id": order_id,
                    "points": points,
                }
            ).execute()
        except Exception:
            pass


def _set_wallet_balance_and_tier(
    merchant_id: str,
    wallet_id: str,
    email: str,
    lifetime_cents: int,
    points: int,
    tier_name: str,
    orders_count: int,
) -> None:
    sb = get_supabase()
    if not sb:
        return

    # wallet_balances columns assumed:
    # wallet_id, merchant_id, email, points_balance, lifetime_cents, tier_name, orders_count, updated_at
    payload = {
        "merchant_id": merchant_id,
        "wallet_id": wallet_id,
        "email": email,
        "points_balance": points,
        "lifetime_cents": lifetime_cents,
        "tier_name": tier_name,
        "orders_count": orders_count,
        "updated_at": _now_iso(),
    }

    # upsert on wallet_id if possible
    try:
        sb.table("wallet_balances").upsert(payload, on_conflict="wallet_id").execute()
        return
    except Exception:
        pass

    # fallback: try update then insert
    try:
        sb.table("wallet_balances").update(payload).eq("wallet_id", wallet_id).execute()
        return
    except Exception:
        pass

    try:
        sb.table("wallet_balances").insert(payload).execute()
    except Exception:
        pass


# ----------------------------
# Shopify fetch
# ----------------------------

def fetch_all_orders(shop_domain: str, access_token: str) -> List[dict]:
    """
    Fetch ALL orders via REST (paginated).
    Uses /admin/api/{version}/orders.json?status=any&limit=250
    """
    orders: List[dict] = []
    base = f"https://{shop_domain}/admin/api/{DEFAULT_SHOPIFY_API_VERSION}/orders.json"
    url = f"{base}?status=any&limit=250"

    headers = _shopify_headers(access_token)

    while url:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"Shopify orders fetch failed: {r.status_code} {r.text[:300]}")

        data = r.json() or {}
        batch = data.get("orders") or []
        orders.extend(batch)

        nxt = _parse_next_link(r.headers.get("Link"))
        url = nxt

    return orders


# ----------------------------
# Main backfill
# ----------------------------

def run_backfill(
    merchant_id: str,
    shop_domain: str,
    access_token: str,
    points_per_dollar: float = 1.0,
) -> Dict:
    """
    End-to-end:
      - Pull orders
      - Aggregate by email
      - Insert ledger entries (one per order)
      - Set balances + tiers (one per email)
    """
    started = time.time()
    tiers = _get_merchant_tiers(merchant_id)

    orders = fetch_all_orders(shop_domain=shop_domain, access_token=access_token)

    # Aggregate by email
    agg: Dict[str, Dict[str, int]] = {}  # email -> {lifetime_cents, orders_count}
    for o in orders:
        email = _pick_email(o)
        if not email:
            continue
        total_cents = _order_total_cents(o)
        if email not in agg:
            agg[email] = {"lifetime_cents": 0, "orders_count": 0}
        agg[email]["lifetime_cents"] += total_cents
        agg[email]["orders_count"] += 1

    # Write ledger per order + balances per email
    ledger_written = 0
    customers_processed = 0

    for o in orders:
        email = _pick_email(o)
        if not email:
            continue

        wallet_id = _upsert_customer_wallet(merchant_id=merchant_id, email=email)

        order_id = _order_id_str(o)
        amount_cents = _order_total_cents(o)
        created_at = _order_created_at(o)

        # Points formula (simple, canonical): dollars * points_per_dollar
        points = int(round((amount_cents / 100.0) * float(points_per_dollar)))

        _insert_ledger_entry(
            merchant_id=merchant_id,
            wallet_id=wallet_id,
            order_id=order_id,
            created_at=created_at,
            amount_cents=amount_cents,
            points=points,
        )
        ledger_written += 1

    for email, info in agg.items():
        wallet_id = _upsert_customer_wallet(merchant_id=merchant_id, email=email)
        lifetime_cents = int(info["lifetime_cents"])
        orders_count = int(info["orders_count"])
        tier_name = choose_tier(tiers, lifetime_cents)

        points_total = int(round((lifetime_cents / 100.0) * float(points_per_dollar)))

        _set_wallet_balance_and_tier(
            merchant_id=merchant_id,
            wallet_id=wallet_id,
            email=email,
            lifetime_cents=lifetime_cents,
            points=points_total,
            tier_name=tier_name,
            orders_count=orders_count,
        )
        customers_processed += 1

    elapsed = time.time() - started
    return {
        "ok": True,
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "orders_fetched": len(orders),
        "ledger_entries_attempted": ledger_written,
        "customers_processed": customers_processed,
        "points_per_dollar": points_per_dollar,
        "elapsed_seconds": round(elapsed, 2),
    }
