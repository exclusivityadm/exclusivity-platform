# apps/backend/services/shopify/sync_products.py
# =====================================================
# Product sync: Shopify -> Supabase
# =====================================================

from __future__ import annotations

from typing import Dict, Any, List
from apps.backend.services.shopify.client import ShopifyClient
from apps.backend.services.supabase_admin_client import SupabaseAdminClient


def sync_products(shop_domain: str, merchant_id: str) -> Dict[str, Any]:
    sb = SupabaseAdminClient()
    sc = ShopifyClient(shop_domain, merchant_id)

    out = {"count": 0}
    page = sc.get("/products.json", params={"limit": 250})
    products: List[Dict[str, Any]] = page.get("products", [])

    for p in products:
        payload = {
            "merchant_id": merchant_id,
            "shop_domain": shop_domain,
            "shopify_product_id": p.get("id"),
            "title": p.get("title"),
            "status": p.get("status"),
            "vendor": p.get("vendor"),
            "product_type": p.get("product_type"),
            "raw": p,
        }
        sb.upsert(
            "shopify_products",
            payload,
            on_conflict="shopify_product_id",
        )
        out["count"] += 1

    return out
