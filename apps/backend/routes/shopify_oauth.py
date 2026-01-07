# apps/backend/routes/shopify_oauth.py
# =====================================================
# Exclusivity Backend — Shopify OAuth Routes (Canonical)
#
# Mounted by main.py under prefix "/shopify"
#
# Routes:
#   GET /shopify/install?shop=...
#   GET /shopify/callback?... (Shopify redirect)
#   GET /shopify/status?shop=...
#
# Stores:
# - merchants.shop_domain (key)
# - merchants.merchant_id (uuid) returned by DB
# - shopify_tokens (recommended) or merchants.shopify_access_token (fallback)
# =====================================================

from __future__ import annotations

import os
import time
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse

from apps.backend.services.supabase_admin_client import SupabaseAdminClient
from apps.backend.services.shopify.hmac import verify_shopify_hmac
from apps.backend.services.shopify.oauth import (
    make_state,
    verify_state,
    normalize_shop,
    build_authorize_url,
    exchange_code_for_token,
)

router = APIRouter(tags=["shopify"])


def ok(data):
    return JSONResponse({"ok": True, "data": data})


def err(message: str, details=None, status_code: int = 400):
    payload = {"ok": False, "error": message}
    if details is not None:
        payload["details"] = details
    return JSONResponse(payload, status_code=status_code)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


def _frontend_redirect(base: str, path: str, query: str = "") -> RedirectResponse:
    base = (base or "").rstrip("/")
    path = "/" + (path or "").lstrip("/")
    url = f"{base}{path}"
    if query:
        url = f"{url}?{query.lstrip('?')}"
    return RedirectResponse(url=url, status_code=302)


@router.get("/install")
def install(shop: str):
    """
    Starts OAuth.
    """
    api_key = _env("SHOPIFY_API_KEY")
    api_secret = _env("SHOPIFY_API_SECRET")
    scopes = _env("SHOPIFY_SCOPES", "read_products,read_customers,read_orders")
    app_url = _env("SHOPIFY_APP_URL")  # backend public base, e.g. https://exclusivity-backend.onrender.com
    redirect_path = _env("SHOPIFY_REDIRECT_PATH", "/shopify/callback")

    if not api_key or not api_secret or not app_url:
        return err("Missing Shopify env vars", {"required": ["SHOPIFY_API_KEY", "SHOPIFY_API_SECRET", "SHOPIFY_APP_URL"]}, 500)

    shop_norm = normalize_shop(shop)
    if not shop_norm:
        return err("Missing shop parameter")

    redirect_uri = f"{app_url.rstrip('/')}{redirect_path}"
    state = make_state(shop_norm, api_secret, ttl_seconds=900)

    auth_url = build_authorize_url(
        shop=shop_norm,
        api_key=api_key,
        scopes=scopes,
        redirect_uri=redirect_uri,
        state=state,
    )
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
def callback(request: Request):
    """
    OAuth callback from Shopify.
    Validates:
    - Shopify hmac
    - signed state
    Exchanges code -> access_token
    Stores merchant + token
    Redirects to frontend onboarding.
    """
    api_key = _env("SHOPIFY_API_KEY")
    api_secret = _env("SHOPIFY_API_SECRET")
    frontend_url = _env("FRONTEND_APP_URL")  # e.g. https://exclusivity-platform.vercel.app

    q = dict(request.query_params)

    # 1) verify HMAC
    if not api_secret or not verify_shopify_hmac(q, api_secret):
        return err("Invalid Shopify HMAC", {"query": q}, 400)

    shop = normalize_shop(q.get("shop", ""))
    code = (q.get("code") or "").strip()
    state = (q.get("state") or "").strip()

    if not shop or not code or not state:
        return err("Missing required callback parameters", {"shop": shop, "has_code": bool(code), "has_state": bool(state)}, 400)

    # 2) verify state
    st_ok, st_payload, st_err = verify_state(state, api_secret)
    if not st_ok:
        return err("Invalid state", {"reason": st_err}, 400)

    if normalize_shop(st_payload.get("shop", "")) != shop:
        return err("State/shop mismatch", {"state_shop": st_payload.get("shop"), "shop": shop}, 400)

    # 3) exchange token
    try:
        access_token = exchange_code_for_token(shop=shop, api_key=api_key, api_secret=api_secret, code=code)
    except Exception as e:
        return err("Token exchange failed", {"exception": str(e)}, 500)

    # 4) persist to Supabase
    try:
        sb = SupabaseAdminClient()

        # Upsert merchant by shop_domain. Assumes merchants table has unique shop_domain.
        merchant_row = sb.upsert(
            "merchants",
            {
                "shop_domain": shop,
                "installed": True,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            on_conflict="shop_domain",
        )

        merchant_id = merchant_row.get("merchant_id")

        # Prefer separate shopify_tokens table if present. If it doesn't exist, fall back to merchants column.
        try:
            if merchant_id:
                sb.upsert(
                    "shopify_tokens",
                    {
                        "merchant_id": merchant_id,
                        "shop_domain": shop,
                        "access_token": access_token,
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                    on_conflict="merchant_id",
                )
            else:
                # Fallback: key by shop_domain if DB returns no merchant_id for some reason
                sb.upsert(
                    "shopify_tokens",
                    {
                        "shop_domain": shop,
                        "access_token": access_token,
                        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                    on_conflict="shop_domain",
                )
        except Exception:
            # fallback to merchants.shopify_access_token if shopify_tokens doesn't exist
            sb.upsert(
                "merchants",
                {
                    "shop_domain": shop,
                    "shopify_access_token": access_token,
                    "installed": True,
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                on_conflict="shop_domain",
            )

    except Exception as e:
        return err("Failed to persist OAuth result", {"exception": str(e)}, 500)

    # 5) redirect back to frontend onboarding with shop
    if not frontend_url:
        # If frontend URL is not set, return JSON so you can see it in browser.
        return ok({"shop": shop, "merchant_id": merchant_id, "note": "Set FRONTEND_APP_URL to enable redirect."})

    # Onboarding expects shop in query string
    return _frontend_redirect(frontend_url, "/onboarding", f"shop={shop}")


@router.get("/status")
def status(shop: str):
    """
    Quick check: do we have a stored token for this shop?
    """
    shop_norm = normalize_shop(shop)
    if not shop_norm:
        return err("Missing shop")

    try:
        sb = SupabaseAdminClient()
        m = sb.select_one("merchants", {"shop_domain": shop_norm}, columns="merchant_id,shop_domain,installed,created_at,updated_at")
        if not m:
            return ok({"shop": shop_norm, "installed": False, "merchant_id": None, "token_present": False})

        merchant_id = m.get("merchant_id")

        token_present = False
        try:
            t = None
            if merchant_id:
                t = sb.select_one("shopify_tokens", {"merchant_id": merchant_id}, columns="merchant_id")
            if not t:
                t = sb.select_one("shopify_tokens", {"shop_domain": shop_norm}, columns="shop_domain")
            token_present = bool(t)
        except Exception:
            # fallback: merchants.shopify_access_token
            token_present = bool(m.get("shopify_access_token"))

        return ok(
            {
                "shop": shop_norm,
                "installed": bool(m.get("installed")) if m.get("installed") is not None else True,
                "merchant_id": merchant_id,
                "token_present": token_present,
            }
        )
    except Exception as e:
        return err("Status failed", {"exception": str(e)}, 500)
