# apps/backend/services/daily_briefing.py
# =====================================================
# AI Daily Briefing — Merchant Intelligence Summary
# =====================================================

from typing import Dict, Any, List
from apps.backend.routes.services.supabase_admin import select_many

def build_daily_briefing(*, merchant_id: str, persona: str = "orion") -> Dict[str, Any]:
    """
    Builds a daily intelligence briefing.
    Read-only. Deterministic. Safe.
    """

    # Latest invoice
    invoices = select_many(
        "invoices",
        filters={"merchant_id": merchant_id},
        columns="id,period_start,period_end,status,total_cents,created_at",
        order="created_at.desc",
        limit=1,
    )
    invoice = invoices[0] if invoices else None

    # Latest pricing recommendation
    pricing = select_many(
        "pricing_recommendations",
        filters={"merchant_id": merchant_id},
        columns="id,uplift_percent,buffer_cents,created_at",
        order="created_at.desc",
        limit=1,
    )
    pricing = pricing[0] if pricing else None

    # Mint job health
    mint_jobs = select_many(
        "mint_jobs",
        filters={"merchant_id": merchant_id},
        columns="id,status,attempts,created_at,error_last",
        order="created_at.desc",
        limit=5,
    )

    insights: List[str] = []

    if pricing:
        insights.append(
            f"Latest pricing strategy: {pricing.get('uplift_percent')}% uplift "
            f"+ {pricing.get('buffer_cents')}¢ buffer."
        )
    else:
        insights.append("No pricing recommendations yet. Capture a catalog snapshot to begin optimization.")

    if invoice:
        total = (invoice.get("total_cents") or 0) / 100
        insights.append(f"Latest invoice total: ${total:.2f} ({invoice.get('status')}).")

    retrying = [j for j in mint_jobs if j.get("status") == "retrying"]
    failed = [j for j in mint_jobs if j.get("status") == "failed"]

    if retrying:
        insights.append(f"{len(retrying)} blockchain jobs are retrying.")
    if failed:
        insights.append(f"{len(failed)} blockchain jobs failed and need review.")

    return {
        "ok": True,
        "merchant_id": merchant_id,
        "persona": persona,
        "summary": insights,
        "invoice": invoice,
        "pricing": pricing,
        "mint_jobs": mint_jobs,
    }
