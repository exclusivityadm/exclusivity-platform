from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from apps.backend.db import get_supabase


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_latest_brand(sb, merchant_id: str) -> Dict[str, Any]:
    r = sb.table("merchant_brand").select("*").eq("merchant_id", merchant_id).limit(1).execute()
    return (r.data[0] if r.data else {}) or {}


def _get_latest_pricing(sb, merchant_id: str) -> Dict[str, Any]:
    r = (
        sb.table("merchant_pricing_recommendations")
        .select("*")
        .eq("merchant_id", merchant_id)
        .order("captured_at", desc=True)
        .limit(1)
        .execute()
    )
    return (r.data[0] if r.data else {}) or {}


def _get_loyalty_health(sb, merchant_id: str) -> Dict[str, Any]:
    # Optional: if your loyalty tables exist, we can surface a quick “system health”
    # without forcing anything heavy.
    try:
        # Example: count wallets / ledger rows (safe, small)
        wallets = sb.table("customer_wallets").select("id", count="exact").eq("merchant_id", merchant_id).execute()
        ledger = sb.table("wallet_ledger").select("id", count="exact").eq("merchant_id", merchant_id).execute()
        return {
            "wallets_count": getattr(wallets, "count", None),
            "ledger_rows_count": getattr(ledger, "count", None),
        }
    except Exception:
        return {"wallets_count": None, "ledger_rows_count": None}


def build_daily_briefing(merchant_id: str, persona: str = "orion") -> Dict[str, Any]:
    sb = get_supabase()
    if not sb:
        return {"ok": False, "error": "Supabase not configured"}

    brand = _get_latest_brand(sb, merchant_id)
    pricing = _get_latest_pricing(sb, merchant_id)
    loyalty = _get_loyalty_health(sb, merchant_id)

    program_name = brand.get("program_name") or "Loyalty Program"
    unit_s = brand.get("unit_name_singular") or "Point"
    unit_p = brand.get("unit_name_plural") or "Points"

    buffer_cents = pricing.get("buffer_cents")
    pricing_payload = pricing.get("payload") or {}
    snapshot_error = pricing_payload.get("snapshot_error")

    # Minimal, non-spammy structure:
    # 1) one status line
    # 2) one opportunity
    # 3) one suggested next action
    bullets: List[str] = []

    bullets.append(f"{program_name} is running. Your system is stable.")

    if buffer_cents is not None:
        dollars = float(buffer_cents) / 100.0
        if snapshot_error:
            bullets.append(
                f"Pricing optimization is ready, but Shopify catalog access is limited right now. "
                f"I can still recommend a simple default buffer of ${dollars:.2f} per item."
            )
        else:
            bullets.append(
                f"Pricing optimization: I recommend a default operational buffer of ${dollars:.2f} per item "
                f"to keep {program_name} effortless while protecting margins."
            )
    else:
        bullets.append("Pricing optimization: not generated yet. I can generate it when you’re ready.")

    # Loyalty insight (light)
    if loyalty.get("wallets_count") is not None:
        bullets.append(
            f"Customer intelligence: I currently see {loyalty.get('wallets_count')} customer profiles tracked."
        )

    suggested_action = {
        "type": "pricing.apply_default_buffer",
        "label": "Apply recommended pricing buffer",
        "explanation": "Updates pricing strategy recommendations (does not change Shopify prices automatically unless you approve).",
    }

    briefing = {
        "ok": True,
        "merchant_id": merchant_id,
        "persona": persona,
        "captured_at": _utcnow(),
        "summary": "Daily briefing ready.",
        "bullets": bullets[:4],  # keep it minimal
        "suggested_action": suggested_action,
        "style_rules": {
            "no_crypto_language": True,
            "customer_invisible": True,
            "non_spammy": True,
        },
        "nomenclature": {"unit_singular": unit_s, "unit_plural": unit_p},
    }

    # Persist for observability
    try:
        sb.table("merchant_briefings").insert({
            "merchant_id": merchant_id,
            "persona": persona,
            "payload": briefing,
        }).execute()
    except Exception:
        pass

    return briefing
