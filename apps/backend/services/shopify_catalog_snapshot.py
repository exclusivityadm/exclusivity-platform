from __future__ import annotations

from typing import Any, Dict
from datetime import datetime, timezone

from apps.backend.db import get_supabase
from apps.backend.services.shopify_client import ShopifyClient


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def snapshot_catalog(merchant_id: str) -> Dict[str, Any]:
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

    products = []
    error = None

    try:
        payload, _h = client.get("/products.json", params={"limit": 50})
        products = payload.get("products") or []
    except Exception as e:
        error = str(e)

    sb.table("merchant_catalog_snapshots").insert({
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "payload": {
            "products_count": len(products),
            "products": products,
            "error": error,
        },
    }).execute()

    return {"ok": True, "merchant_id": merchant_id, "shop_domain": shop_domain, "products_count": len(products), "error": error}
