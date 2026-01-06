from __future__ import annotations

from typing import Any, Dict, List, Optional

from apps.backend.routes.services.supabase_admin import select_many, select_one

def _money(cents: Optional[int]) -> str:
    if cents is None:
        return "$0.00"
    return f"${cents/100:.2f}"

def build_daily_briefing(merchant_id: str) -> Dict[str, Any]:
    # Latest invoice
    inv_rows = select_many(
        "invoices",
        filters={"merchant_id": merchant_id},
        columns="id,period_start,period_end,status,subscription_cents,usage_cents,total_cents,created_at",
        order="created_at.desc",
        limit=1,
    )
    invoice = inv_rows[0] if inv_rows else None

    # Latest pricing recommendation
    rec_rows = select_many(
        "pricing_recommendations",
        filters={"merchant_id": merchant_id},
        columns="id,snapshot_id,strategy,uplift_percent,buffer_cents,est_mint_cost_cents,created_at",
        order="created_at.desc",
        limit=1,
    )
    pricing = rec_rows[0] if rec_rows else None

    # Recent mint job outcomes
    mint_rows = select_many(
        "mint_jobs",
        filters={"merchant_id": merchant_id},
        columns="id,job_type,status,attempts,created_at,updated_at,error_last",
        order="created_at.desc",
        limit=10,
    )

    # Minimal “next best actions” (advisory only)
    actions: List[Dict[str, Any]] = []
    if not pricing:
        actions.append({"type": "pricing", "suggestion": "Capture catalog snapshot and generate pricing recommendations."})
    else:
        actions.append({
            "type": "pricing",
            "suggestion": f"Review latest pricing strategy: {pricing.get('uplift_percent')}% uplift + {pricing.get('buffer_cents')}¢ buffer.",
        })

    if invoice:
        actions.append({
            "type": "billing",
            "suggestion": f"Current invoice total: {_money(int(invoice.get('total_cents') or 0))} ({invoice.get('status')}).",
        })

    failed_mints = [m for m in mint_rows if m.get("status") == "failed"]
    retrying_mints = [m for m in mint_rows if m.get("status") == "retrying"]
    if retrying_mints:
        actions.append({"type": "blockchain", "suggestion": f"{len(retrying_mints)} mint jobs are retrying. Monitor /blockchain/worker/tick cadence."})
    if failed_mints:
        actions.append({"type": "blockchain", "suggestion": f"{len(failed_mints)} mint jobs failed. Inspect mint_job_events for details."})

    briefing = {
        "merchant_id": merchant_id,
        "invoice": invoice,
        "pricing": pricing,
        "mint_recent": mint_rows,
        "next_actions": actions[:7],
    }
    return briefing
