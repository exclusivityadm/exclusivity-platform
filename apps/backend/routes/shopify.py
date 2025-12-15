from fastapi import APIRouter

from .services.shopify.shopify_service import ShopifyService


router = APIRouter(prefix="/shopify", tags=["shopify"])

service = ShopifyService()


@router.post("/webhook")
async def shopify_webhook(payload: dict):
    return await service.handle_webhook(payload)
