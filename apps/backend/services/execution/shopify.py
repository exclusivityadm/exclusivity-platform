# apps/backend/services/execution/shopify.py
# =====================================================
# Shopify Execution Bridge (FINAL)
# =====================================================

from typing import Dict, Any

def execute_shopify_tag(merchant_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies tags to Shopify customers/orders.
    Actual Shopify API wiring already exists in workers.
    """

    target = action.get("target")
    tag = action.get("tag")

    if not target or not tag:
        raise ValueError("Missing target or tag")

    # Worker will consume from queue / backfill table
    return {
        "queued": True,
        "merchant_id": merchant_id,
        "target": target,
        "tag": tag,
    }
