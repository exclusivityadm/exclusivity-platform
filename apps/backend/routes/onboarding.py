# apps/backend/routes/onboarding.py

from fastapi import APIRouter, Request
from typing import Any, Dict
import logging

log = logging.getLogger("uvicorn")

router = APIRouter()

# ----------------------------------------------------------
# CANONICAL API RESPONSE HELPERS
# ----------------------------------------------------------

def ok(data: Any) -> Dict[str, Any]:
    return {"ok": True, "data": data}

def err(message: str, details: Any = None) -> Dict[str, Any]:
    payload = {"ok": False, "error": message}
    if details is not None:
        payload["details"] = details
    return payload

# ----------------------------------------------------------
# MERCHANT RESOLUTION (STUB — SAFE FOR NOW)
# ----------------------------------------------------------
# This is intentionally conservative and deterministic.
# We can wire Supabase later without changing the contract.

def normalize_shop(shop: str) -> str:
    return shop.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")

async def resolve_merchant(shop: str) -> Dict[str, Any]:
    if not shop:
        return err("Missing shop parameter")

    shop = normalize_shop(shop)

    # TEMPORARY LOGIC:
    # Treat any shop as resolvable for now.
    # Later: replace with Supabase lookup + create.
    merchant_id = f"m_{abs(hash(shop))}"

    return ok({
        "merchant_id": merchant_id,
        "shop_domain": shop,
        "created": False
    })

# ----------------------------------------------------------
# ROUTES
# ----------------------------------------------------------

@router.post("/resolve")
async def onboarding_resolve(request: Request):
    try:
        body = await request.json()
        shop = body.get("shop") or request.query_params.get("shop")

        return await resolve_merchant(shop)

    except Exception as e:
        log.exception("Onboarding resolve failed")
        return err("Onboarding resolve failed", str(e))
