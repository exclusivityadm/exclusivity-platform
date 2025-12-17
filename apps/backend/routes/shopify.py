from fastapi import APIRouter

# ❌ NO prefix here — mounted in main.py
router = APIRouter(tags=["shopify"])


@router.post("/webhook")
async def webhook(payload: dict):
    return {"ok": True}
