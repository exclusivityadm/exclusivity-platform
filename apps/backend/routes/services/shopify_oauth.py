# apps/backend/routes/shopify_oauth.py
# =====================================================
# Shopify OAuth Routes (Canonical – Production)
#
# Mounted under /shopify by main.py
#
#   GET  /shopify/auth?shop=...
#   GET  /shopify/callback?shop=...&code=...&hmac=...&state=...&timestamp=...
#
# Behavior:
# - Redirects merchant to Shopify install URL
# - Validates callback HMAC + state
# - Exchanges access token
# - Upserts merchant + token row in Supabase (service role)
# - Registers day-one webhooks
# - Redirects merchant to FRONTEND onboarding (absolute URL)
# =====================================================

from __future__ import annotations

import os
import secrets
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from typing import Dict

from apps.backend.routes.services.shopify_crypto import (
    normalize_shop,
    verify_hmac,
    build_state,
    parse_state,
)

from apps.backend.routes.services.shopify_client import (
    build_install_url,
    exchange_access_token,
    register_webhook,
    ShopifyClientError,
)

from apps.backend.routes.services.supabase_service import (
    upsert,
    select_one,
    SupabaseServiceError,
)

router = APIRouter(tags=["shopify"])


# -----------------------------------------------------
# Helpers
# -----------------------------------------------------

def backend_public_url() -> str:
    v = (os.getenv("SHOPIFY_APP_URL") or "").strip().rstrip("/")
    if not v:
        raise HTTPException(500, "Missing SHOPIFY_APP_URL")
    return v


def frontend_public_url() -> str:
    v = (os.getenv("FRONTEND_APP_URL") or "").strip().rstrip("/")
    if not v:
        raise HTTPException(500, "Missing FRONTEND_APP_URL")
    return v


# -----------------------------------------------------
# OAuth Start
# -----------------------------------------------------

@router.get("/auth")
def shopify_auth(shop: str):
    shop = normalize_shop(shop)
    if not shop:
        raise HTTPException(400, "Missing shop")

    nonce = secrets.token_urlsafe(16)
    state = build_state(shop, nonce)

    install_url = build_install_url(shop, state)
    return RedirectResponse(url=install_url, status_code=302)


# -----------------------------------------------------
# OAuth Callback
# -----------------------------------------------------

@router.get("/callback")
async def shopify_callback(request: Request):
    q: Dict[str, str] = dict(request.query_params)

    shop = normalize_shop(q.get("shop", ""))
    code = (q.get("code") or "").strip()
    state = (q.get("state") or "").strip()

    if not shop:
        raise HTTPException(400, "Missing shop")
    if not code:
        raise HTTPException(400, "Missing code")
    if not state:
        raise HTTPException(400, "Missing state")

    secret = (os.getenv("SHOPIFY_API_SECRET") or "").strip()
    if not verify_hmac(q, secret):
        raise HTTPException(401, "Invalid HMAC")

    parsed = parse_state(state)
    if not parsed or normalize_shop(parsed.get("shop", "")) != shop:
        raise HTTPException(401, "Invalid state")

    try:
        token_resp = exchange_access_token(shop, code)
        access_token = (token_resp.get("access_token") or "").strip()
        scope = (token_resp.get("scope") or "").strip()

        if not access_token:
            raise HTTPException(500, "Token exchange returned no access_token")

        # Resolve or create merchant
        merchant = select_one(
            "merchants",
            {"shop_domain": shop},
            columns="merchant_id,shop_domain,installed",
        )

        if merchant and merchant.get("merchant_id"):
            merchant_id = merchant["merchant_id"]
        else:
            created = upsert(
                "merchants",
                {"shop_domain": shop, "installed": True},
                on_conflict="shop_domain",
            )
            merchant_id = created.get("merchant_id")

        if not merchant_id:
            raise HTTPException(500, "Unable to resolve merchant_id")

        # Persist token
        upsert(
            "merchants",
            {"merchant_id": merchant_id, "installed": True},
            on_conflict="merchant_id",
        )

        upsert(
            "shopify_tokens",
            {
                "merchant_id": merchant_id,
                "shop_domain": shop,
                "access_token": access_token,
                "scope": scope,
            },
            on_conflict="merchant_id",
        )

        # Register essential webhooks
        base = backend_public_url()
        register_webhook(shop, access_token, "app/uninstalled", f"{base}/shopify/webhooks/app_uninstalled")
        register_webhook(shop, access_token, "customers/create", f"{base}/shopify/webhooks/customers_create")
        register_webhook(shop, access_token, "orders/create", f"{base}/shopify/webhooks/orders_create")

        # -------------------------------------------------
        # FINAL REDIRECT (ABSOLUTE – REQUIRED BY SHOPIFY)
        # -------------------------------------------------
        frontend = frontend_public_url()
        return RedirectResponse(
            url=f"{frontend}/onboarding?shop={shop}",
            status_code=302,
        )

    except ShopifyClientError as e:
        raise HTTPException(500, f"shopify oauth error: {e}")
    except SupabaseServiceError as e:
        raise HTTPException(500, f"supabase error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"shopify/callback unexpected: {e}")
