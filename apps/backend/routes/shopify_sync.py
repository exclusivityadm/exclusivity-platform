# apps/backend/routes/shopify_sync.py
# =====================================================
# Shopify Sync Routes (Manual triggers)
#
# Mounted under /shopify by main.py
#
# Routes:
#   POST /shopify/sync/products
#   POST /shopify/sync/customers
#   POST /shopify/sync/orders
# =====================================================

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from apps.backend.routes.services.supabase_admin import select_one
from apps.backend.services.shopify.sync_products import sync_products
from apps.backend.services.shopify.sync_customers import sync_customers
from apps.backend.services.shopify.sync_orders import sync_orders

router = APIRouter(tags=["shopify"])


def ok(data):
    return JSONResponse({"ok": True, "data": data})


def err(msg: str):
    return JSONResponse({"ok": False, "error": msg}, status_code=400)


def _resolve(shop: str):
    m = select_one("merchants", {"shop_domain": shop}, columns="merchant_id,shop_domain")
    if not m or not m.get("merchant_id"):
        raise HTTPException(404, "Merchant not resolved")
    return m.get("merchant_id")


@router.post("/sync/products")
def sync_products_route(shop: str):
    merchant_id = _resolve(shop)
    return ok(sync_products(shop, merchant_id))


@router.post("/sync/customers")
def sync_customers_route(shop: str):
    merchant_id = _resolve(shop)
    return ok(sync_customers(shop, merchant_id))


@router.post("/sync/orders")
def sync_orders_route(shop: str):
    merchant_id = _resolve(shop)
    return ok(sync_orders(shop, merchant_id))
