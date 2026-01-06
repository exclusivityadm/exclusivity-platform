import requests
from typing import Dict, Optional

from apps.backend.lib.supabase_admin import upsert_one, insert_one

SHOPIFY_API_VERSION = "2024-10"
ORDERS_PAGE_LIMIT = 50


async def run_backfill_slice(
    *,
    merchant_id: str,
    shop_domain: str,
    access_token: str,
    points_per_dollar: float,
    cursor: Optional[str],
    max_pages: int = 5,
) -> Dict[str, Optional[str]]:
    """
    Runs a bounded slice of the Shopify backfill.

    Returns:
    {
        "done": bool,
        "next_cursor": str | None,
        "orders_processed": int,
        "customers_touched": int
    }
    """

    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }

    orders_processed = 0
    customers_touched = set()
    page_count = 0
    next_cursor = cursor

    while page_count < max_pages:
        url = (
            f"https://{shop_domain}/admin/api/{SHOPIFY_API_VERSION}/orders.json"
            f"?limit={ORDERS_PAGE_LIMIT}&status=any"
        )
        if next_cursor:
            url += f"&page_info={next_cursor}"

        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        orders = data.get("orders", [])

        if not orders:
            return {
                "done": True,
                "next_cursor": None,
                "orders_processed": orders_processed,
                "customers_touched": len(customers_touched),
            }

        for order in orders:
            order_id = str(order["id"])
            email = order.get("email")
            total_price = float(order.get("total_price", 0))
            points = int(total_price * points_per_dollar)

            if not email:
                continue

            customer = upsert_one(
                "loyalty_customers",
                {
                    "merchant_id": merchant_id,
                    "email": email,
                },
                conflict_cols="merchant_id,email",
            )

            customers_touched.add(customer["id"])

            try:
                insert_one(
                    "wallet_ledger",
                    {
                        "merchant_id": merchant_id,
                        "customer_id": customer["id"],
                        "amount": points,
                        "direction": "earn",
                        "source": "shopify_order",
                        "source_ref": order_id,
                    },
                )
            except Exception:
                # Idempotency violation = already processed
                pass

            orders_processed += 1

        link_header = resp.headers.get("Link", "")
        if 'rel="next"' not in link_header:
            return {
                "done": True,
                "next_cursor": None,
                "orders_processed": orders_processed,
                "customers_touched": len(customers_touched),
            }

        # Extract page_info cursor
        next_cursor = (
            link_header.split("page_info=")[1].split(">")[0]
            if "page_info=" in link_header
            else None
        )

        page_count += 1

    return {
        "done": False,
        "next_cursor": next_cursor,
        "orders_processed": orders_processed,
        "customers_touched": len(customers_touched),
    }
