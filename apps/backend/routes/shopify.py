from fastapi import APIRouter

from .services.shopify_webhooks import ShopifyWebhooksService

router = APIRouter(prefix="/shopify", tags=["shopify"])
service = ShopifyWebhooksService()


@router.post("/webhook")
async def webhook(payload: dict):
    return await service.handle(payload)
