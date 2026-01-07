# apps/backend/routes/shopify.py
# =====================================================
# Exclusivity Backend — Shopify Routes (Canonical Stub)
#
# Mounted by main.py under prefix "/shopify"
# Keep lightweight now; expand later for webhooks/proxy calls.
# =====================================================

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["shopify"])


@router.get("/ping")
def ping():
    return JSONResponse({"ok": True, "data": {"shopify": "reachable"}})
