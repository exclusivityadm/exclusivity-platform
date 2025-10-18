from fastapi import APIRouter, HTTPException
import httpx
from ..config import env

router = APIRouter()

@router.get("/sync")
async def sync_customers():
    store = env("SHOPIFY_STORE_URL")
    token = env("SHOPIFY_ACCESS_TOKEN")
    api_version = env("SHOPIFY_API_VERSION","2025-01")
    if not store or not token:
        raise HTTPException(status_code=400, detail="Shopify credentials missing")
    url = f"https://{store}/admin/api/{api_version}/shop.json"
    headers = {"X-Shopify-Access-Token": token}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, headers=headers)
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=f"Shopify error: {r.text}")
    return {"ok": True, "shop": r.json().get("shop",{}).get("name","(unknown)")}
