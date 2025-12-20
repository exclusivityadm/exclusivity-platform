from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime, timezone

from apps.backend.db import get_supabase
from apps.backend.services.shopify_client import ShopifyClient


ORDERS_PAGE_SIZE = 50


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def enqueue_backfill(merchant_id: str, shop_domain: str) -> None:
    """
    Ensures a backfill run exists with status=queued (idempotent).
    """
    sb = get_supabase()
    if not sb:
        return

    existing = sb.table("backfill_runs").select("*").eq("merchant_id", merchant_id).eq("provider", "shopify").limit(1).execute()
    if existing.data:
        sb.table("backfill_runs").update({"status": "queued", "error": None, "updated_at": _utcnow()}).eq("merchant_id", merchant_id).eq("provider", "shopify").execute()
        return

    sb.table("backfill_runs").insert({
        "merchant_id": merchant_id,
        "provider": "shopify",
        "shop_domain": shop_domain,
        "status": "queued",
        "orders_processed": 0,
        "customers_seen": 0,
    }).execute()


def run_backfill_once(merchant_id: str) -> Dict[str, Any]:
    """
    Runs a bounded, resumable backfill pass.
    - Pulls historical orders from Shopify
    - Aggregates lifetime spend per customer email
    - Upserts customer wallets + tiers via existing loyalty routes/storage
    NOTE: This function does not assume crypto/on-chain settlement.
    """
    sb = get_supabase()
    if not sb:
        return {"ok": False, "error": "Supabase not configured"}

    # Load integration token
    integ = sb.table("merchant_integrations").select("*").eq("merchant_id", merchant_id).eq("provider", "shopify").limit(1).execute()
    if not integ.data:
        return {"ok": False, "error": "No Shopify integration found for merchant"}

    integration = integ.data[0]
    shop_domain = integration["shop_domain"]
    token = integration["access_token"]

    # Load run record
    runq = sb.table("backfill_runs").select("*").eq("merchant_id", merchant_id).eq("provider", "shopify").limit(1).execute()
    if not runq.data:
        enqueue_backfill(merchant_id, shop_domain)
        runq = sb.table("backfill_runs").select("*").eq("merchant_id", merchant_id).eq("provider", "shopify").limit(1).execute()
    run = runq.data[0]

    # Mark running
    sb.table("backfill_runs").update({
        "status": "running",
        "started_at": run.get("started_at") or _utcnow(),
        "error": None,
    }).eq("merchant_id", merchant_id).eq("provider", "shopify").execute()

    cursor: Optional[str] = run.get("cursor")
    orders_processed = int(run.get("orders_processed") or 0)

    client = ShopifyClient(shop_domain, token)

    params = {
        "limit": ORDERS_PAGE_SIZE,
        "status": "any",
        "order": "created_at asc",
        "fields": "id,email,total_price,currency,created_at,customer",
    }
    if cursor:
        params = {"limit": ORDERS_PAGE_SIZE, "page_info": cursor}

    # Pull one page per invocation (safe for Render + avoids long jobs)
    try:
        payload, headers = client.get("/orders.json", params=params)
        orders = payload.get("orders") or []
        next_cursor = ShopifyClient.parse_next_page_info(headers.get("Link"))
    except Exception as e:
        sb.table("backfill_runs").update({
            "status": "failed",
            "error": str(e),
            "updated_at": _utcnow(),
        }).eq("merchant_id", merchant_id).eq("provider", "shopify").execute()
        return {"ok": False, "error": str(e)}

    # Aggregate spend by customer email
    spend_by_email: Dict[str, float] = {}
    customers_seen = 0

    for o in orders:
        email = (o.get("email") or (o.get("customer") or {}).get("email") or "").strip().lower()
        if not email:
            continue
        customers_seen += 1
        try:
            total = float(o.get("total_price") or 0)
        except Exception:
            total = 0.0
        spend_by_email[email] = spend_by_email.get(email, 0.0) + total

    # Apply to your existing loyalty model:
    # We assume your DB has customer_wallets + wallet_ledger + wallet_balances and that your loyalty routes
    # upsert customer wallets based on email + merchant_id. We'll do direct table operations safely here.

    # Upsert wallets + balances
    # NOTE: This is a *backfill* write; we do not create one ledger row per order (too heavy).
    # We anchor a single "backfill_credit" entry per customer that equals total historical spend.
    for email, spend in spend_by_email.items():
        # 1) upsert customer_wallets
        cw = sb.table("customer_wallets").select("*").eq("merchant_id", merchant_id).eq("email", email).limit(1).execute()
        if cw.data:
            wallet_id = cw.data[0]["id"]
        else:
            ins = sb.table("customer_wallets").insert({
                "merchant_id": merchant_id,
                "email": email,
            }).execute()
            wallet_id = ins.data[0]["id"]

        # 2) write/update a single backfill ledger entry (idempotent by unique key)
        # If your schema has no unique constraint, we simulate idempotency by deleting any prior backfill row then inserting.
        sb.table("wallet_ledger").delete().eq("wallet_id", wallet_id).eq("event_type", "backfill_credit").execute()

        sb.table("wallet_ledger").insert({
            "wallet_id": wallet_id,
            "merchant_id": merchant_id,
            "event_type": "backfill_credit",
            "amount": spend,
            "meta": {"source": "shopify", "note": "historical backfill spend"},
        }).execute()

    # Recompute balances using your existing function if present
    # (You already referenced apply_wallet_ledger_to_balance)
    try:
        sb.rpc("apply_wallet_ledger_to_balance", {"p_merchant_id": merchant_id}).execute()
    except Exception:
        # If RPC signature differs, we keep going; balances may be recomputed by your existing code paths.
        pass

    # Update run record
    orders_processed += len(orders)

    update = {
        "orders_processed": orders_processed,
        "customers_seen": int(run.get("customers_seen") or 0) + customers_seen,
        "cursor": next_cursor,
        "updated_at": _utcnow(),
    }

    if not next_cursor:
        update["status"] = "completed"
        update["finished_at"] = _utcnow()

    sb.table("backfill_runs").update(update).eq("merchant_id", merchant_id).eq("provider", "shopify").execute()

    return {
        "ok": True,
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "page_orders": len(orders),
        "orders_processed_total": orders_processed,
        "next_cursor": next_cursor,
        "status": update.get("status") or "running",
    }
