from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone

from apps.backend.db import get_supabase
from apps.backend.services.shopify_client import ShopifyClient


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_get(d: dict, *keys: str) -> Optional[Any]:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _extract_brand_from_settings_json(settings: dict) -> Dict[str, Optional[str]]:
    """
    Heuristic extraction from theme settings_data.json.
    Shopify themes vary wildly; this must be resilient.
    """
    # Common places:
    # settings_data.json often includes: current -> settings -> color_* or typography
    current = settings.get("current") or settings.get("presets") or {}
    # Try both shapes:
    base_settings = None

    if isinstance(current, dict) and "settings" in current:
        base_settings = current.get("settings") or {}
    elif isinstance(settings.get("current"), dict):
        base_settings = (settings.get("current") or {}).get("settings") or {}

    base_settings = base_settings or {}

    # Common field name guesses (will be None if absent)
    primary = (
        base_settings.get("color_primary")
        or base_settings.get("colors_accent_1")
        or base_settings.get("accent_1")
        or base_settings.get("color_accent")
        or base_settings.get("color_button")
    )
    secondary = (
        base_settings.get("color_secondary")
        or base_settings.get("colors_accent_2")
        or base_settings.get("accent_2")
        or base_settings.get("color_background")
    )

    font = (
        base_settings.get("type_body_font")
        or base_settings.get("type_header_font")
        or base_settings.get("font_body")
        or base_settings.get("font_heading")
    )

    # Normalize to strings
    def norm(v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            return v.strip()[:120]
        if isinstance(v, dict):
            # Shopify often stores font as { "family": "...", "fallback_families": "...", ... }
            fam = v.get("family") or v.get("name")
            if isinstance(fam, str):
                return fam.strip()[:120]
        return None

    return {
        "primary_color": norm(primary),
        "secondary_color": norm(secondary),
        "font_family": norm(font),
    }


def ingest_brand(merchant_id: str) -> Dict[str, Any]:
    """
    Pulls Shopify shop + theme settings (best-effort), stores into merchant_brand.
    Safe to run multiple times.
    """
    sb = get_supabase()
    if not sb:
        return {"ok": False, "error": "Supabase not configured"}

    integ = sb.table("merchant_integrations").select("*").eq("merchant_id", merchant_id).eq("provider", "shopify").limit(1).execute()
    if not integ.data:
        return {"ok": False, "error": "No Shopify integration found"}

    integration = integ.data[0]
    shop_domain = integration["shop_domain"]
    token = integration["access_token"]
    client = ShopifyClient(shop_domain, token)

    # Ensure merchant_brand exists
    br = sb.table("merchant_brand").select("*").eq("merchant_id", merchant_id).limit(1).execute()
    if not br.data:
        sb.table("merchant_brand").insert({
            "merchant_id": merchant_id,
            "shop_domain": shop_domain,
            "program_name": "Loyalty Program",
            "unit_name_singular": "Point",
            "unit_name_plural": "Points",
            "onboarding_completed": False,
        }).execute()

    # 1) Shop metadata (usually available without special theme scopes)
    shop_name = None
    try:
        payload, _headers = client.get("/shop.json")
        shop_name = _safe_get(payload, "shop", "name")
    except Exception:
        # non-fatal
        pass

    update: Dict[str, Any] = {"shop_domain": shop_domain, "updated_at": _utcnow()}
    if isinstance(shop_name, str) and shop_name.strip():
        update["brand_name"] = shop_name.strip()[:120]

    # 2) Theme settings (best-effort; may require read_themes which some setups don’t show)
    # We degrade gracefully if forbidden.
    theme_bits: Dict[str, Optional[str]] = {}
    try:
        themes, _h = client.get("/themes.json", params={"fields": "id,role,name"})
        theme_id = None
        for t in (themes.get("themes") or []):
            if t.get("role") == "main":
                theme_id = t.get("id")
                break

        if theme_id:
            # Try to read settings_data.json
            settings_payload, _h2 = client.get(
                f"/themes/{theme_id}/assets.json",
                params={"asset[key]": "config/settings_data.json"}
            )
            settings_value = _safe_get(settings_payload, "asset", "value")
            if isinstance(settings_value, str) and settings_value.strip():
                import json
                parsed = json.loads(settings_value)
                theme_bits = _extract_brand_from_settings_json(parsed)
    except Exception:
        # non-fatal
        theme_bits = {}

    # Apply theme bits
    for k, v in theme_bits.items():
        if v:
            update[k] = v

    sb.table("merchant_brand").update(update).eq("merchant_id", merchant_id).execute()

    return {"ok": True, "merchant_id": merchant_id, "shop_domain": shop_domain, "saved": list(update.keys())}
