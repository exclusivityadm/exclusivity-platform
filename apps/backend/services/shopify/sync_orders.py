# apps/backend/services/shopify/sync_orders.py
# =====================================================
# Order sync: Shopify -> Supabase
# =====================================================

from __future__ import annotations

from typing import Dict, Any, List
from apps.backend.services.shopify.client import ShopifyClient
from apps.backend.services.supabase_admin_client import SupabaseAdminClient


def sync_orders(shop_domain: str, merchant_id: str) -> Dict[str, Any]:
    sb = SupabaseAdminClient()
    sc = ShopifyClient(shop_domain, merchant_id)

    out = {"count": 0}
    page = sc.get("/orders.json", params={"limit": 250, "status": "any"})
    orders: List[Dict[str, Any]] = page.get("orders", [])

    for o in orders:
        payload = {
            "merchant_id": merchant_id,
            "shop_domain": shop_domain,
            "shopify_order_id": o.get("id"),
            "order_number": o.get("order_number"),
            "financial_status": o.get("financial_status"),
            "fulfillment_status": o.get("fulfillment_status"),
            "currency": o.get("currency"),
            "total_price": o.get("total_price"),
            "raw": o,
        }
        sb.upsert(
            "shopify_orders",
            payload,
            on_conflict="shopify_order_id",
        )
        out["count"] += 1

    return out
