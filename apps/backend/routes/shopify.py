from fastapi import APIRouter

router = APIRouter(prefix="/shopify", tags=["shopify"])


@router.post("/webhook")
async def webhook(payload: dict):
    return {"ok": True}
