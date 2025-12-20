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


def ingest_brand(merchant_id: str) -> Dict[str, Any]:
    sb = get_supabase()
    if not sb:
        return {"ok": False, "error": "Supabase not configured"}

    integ = (
        sb.table("merchant_integrations")
        .select("*")
        .eq("merchant_id", merchant_id)
        .eq("provider", "shopify")
        .limit(1)
        .execute()
    )
    if not integ.data:
        return {"ok": False, "error": "No Shopify integration found for merchant_id"}

    integration = integ.data[0]
    shop_domain = integration["shop_domain"]
    token = integration["access_token"]
    client = ShopifyClient(shop_domain, token)

    # Shop metadata (best-effort)
    shop_name = None
    try:
        payload, _headers = client.get("/shop.json")
        shop_name = _safe_get(payload, "shop", "name")
    except Exception:
        pass

    update: Dict[str, Any] = {"shop_domain": shop_domain, "updated_at": _utcnow()}
    if isinstance(shop_name, str) and shop_name.strip():
        update["brand_name"] = shop_name.strip()[:120]

    sb.table("merchant_brand").update(update).eq("merchant_id", merchant_id).execute()
    return {"ok": True, "merchant_id": merchant_id, "shop_domain": shop_domain, "saved": list(update.keys())}
