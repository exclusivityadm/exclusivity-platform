# apps/backend/routes/shopify.py
# =====================================================
# Shopify Routes (Canonical)
# =====================================================

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.backend.routes.shopify_sync import router as sync_router

router = APIRouter(tags=["shopify"])


@router.get("/ping")
def ping():
    return JSONResponse({"ok": True, "data": {"shopify": "reachable"}})


# mount sync subroutes
router.include_router(sync_router)
