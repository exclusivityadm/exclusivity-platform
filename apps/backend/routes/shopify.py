from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
import os
from urllib.parse import urlencode

from apps.backend.services.shopify_oauth import (
    build_install_url, verify_hmac, exchange_code_for_token, new_state
)
from apps.backend.services.merchant_service import upsert_merchant_from_shopify

router = APIRouter(prefix="/shopify", tags=["shopify"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://exclusivity-platform.vercel.app").rstrip("/")

@router.get("/install")
def install(shop: str):
    """
    Start OAuth install. Example:
    /shopify/install?shop=exclusivity-dev.myshopify.com
    """
    if not shop or ".myshopify.com" not in shop:
        raise HTTPException(status_code=400, detail="Missing or invalid shop param (must be *.myshopify.com).")

    state = new_state()
    url = build_install_url(shop=shop, state=state)

    # NOTE: For Drop A speed, we do not persist state server-side.
    # Shopify includes state; we will accept and use it as provided on callback.
    return RedirectResponse(url, status_code=302)

@router.get("/callback")
def callback(request: Request):
    """
    Shopify redirects here after auth. We verify HMAC, exchange code for token,
    upsert merchant in Supabase, then redirect to frontend onboarding.
    """
    qp = dict(request.query_params)

    if not verify_hmac(qp):
        raise HTTPException(status_code=401, detail="Invalid Shopify HMAC on callback.")

    shop = qp.get("shop")
    code = qp.get("code")
    if not shop or not code:
        raise HTTPException(status_code=400, detail="Missing shop or code on callback.")

    token = exchange_code_for_token(shop=shop, code=code)
    merchant = upsert_merchant_from_shopify(shop_domain=shop, access_token=token)

    # Redirect merchant into onboarding UI
    onboarding_url = f"{FRONTEND_URL}/onboarding?" + urlencode({
        "merchant_id": merchant["id"],
        "shop": shop
    })
    return RedirectResponse(onboarding_url, status_code=302)

@router.get("/status")
def status():
    return JSONResponse({"ok": True})
