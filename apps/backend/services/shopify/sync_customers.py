# apps/backend/services/shopify/sync_customers.py
# =====================================================
# Customer sync: Shopify -> Supabase
# =====================================================

from __future__ import annotations

from typing import Dict, Any, List
from apps.backend.services.shopify.client import ShopifyClient
from apps.backend.services.supabase_admin_client import SupabaseAdminClient


def sync_customers(shop_domain: str, merchant_id: str) -> Dict[str, Any]:
    sb = SupabaseAdminClient()
    sc = ShopifyClient(shop_domain, merchant_id)

    out = {"count": 0}
    page = sc.get("/customers.json", params={"limit": 250})
    customers: List[Dict[str, Any]] = page.get("customers", [])

    for c in customers:
        payload = {
            "merchant_id": merchant_id,
            "shop_domain": shop_domain,
            "shopify_customer_id": c.get("id"),
            "email": c.get("email"),
            "first_name": c.get("first_name"),
            "last_name": c.get("last_name"),
            "state": c.get("state"),
            "raw": c,
        }
        sb.upsert(
            "shopify_customers",
            payload,
            on_conflict="shopify_customer_id",
        )
        out["count"] += 1

    return out
