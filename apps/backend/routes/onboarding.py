# apps/backend/routes/onboarding.py

from fastapi import APIRouter, Request
from apps.backend.services.merchant.service import resolve_or_create_merchant

router = APIRouter()

@router.post("/resolve")
async def onboarding_resolve(request: Request):
    body = await request.json()
    shop = body.get("shop") or request.query_params.get("shop")
    return await resolve_or_create_merchant(shop)
