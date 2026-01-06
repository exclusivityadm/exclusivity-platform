from fastapi import APIRouter

from apps.backend.routes.shopify import router as shopify_router
from apps.backend.routes.shopify_backfill_worker import router as shopify_backfill_worker_router

router = APIRouter()

# Core Shopify integration surface
router.include_router(shopify_router)

# Backfill worker engine
router.include_router(shopify_backfill_worker_router)
