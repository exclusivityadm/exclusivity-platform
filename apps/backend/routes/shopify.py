# apps/backend/routes/shopify.py
# =====================================================
# Exclusivity Backend — Shopify Routes (Webhooks + Backfill Worker)
#
# Mounted at: /shopify (prefix owned by main.py)
#
# Webhooks (HMAC-verified):
#   POST /shopify/webhooks/orders/create
#   POST /shopify/webhooks/orders/updated
#   POST /shopify/webhooks/customers/create
#   POST /shopify/webhooks/app/uninstalled
#
# Backfill (secure worker):
#   POST /shopify/backfill/enqueue?shop_domain=...&types=orders,customers,products
#   POST /shopify/backfill/worker/once?merchant_id=...&max_items=50
#
# Security:
# - Worker endpoints require header: X-Worker-Token == BACKFILL_WORKER_TOKEN
# - Supabase calls use SERVICE ROLE key only
# =====================================================

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["shopify"])  # prefix owned by main.py


# -----------------------------------------------------
# Env
# -----------------------------------------------------

def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


def _must_env(name: str) -> str:
    v = _env(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


# -----------------------------------------------------
# Shopify HMAC verification (webhooks)
# -----------------------------------------------------

def verify_shopify_hmac(raw_body: bytes, hmac_header: str, secret: str) -> bool:
    """
    Shopify sends base64(hmac_sha256(body, secret)) in X-Shopify-Hmac-Sha256
    """
    if not hmac_header:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)


def _shop_domain_from_headers(request: Request) -> str:
    shop = (request.headers.get("X-Shopify-Shop-Domain") or "").strip().lower()
    if not shop:
        shop = (request.headers.get("host") or "").strip().lower()
    return shop


async def _handle_webhook(request: Request) -> Tuple[str, Dict[str, Any]]:
    raw = await request.body()
    secret = _must_env("SHOPIFY_API_SECRET")
    hmac_header = (_env("SHOPIFY_WEBHOOK_TOLERATE_MISSING_HMAC", "false").lower() == "true") and (request.headers.get("X-Shopify-Hmac-Sha256") or "").strip()

    # normal path: require header
    hdr = (request.headers.get("X-Shopify-Hmac-Sha256") or "").strip()
    tolerate_missing = _env("SHOPIFY_WEBHOOK_TOLERATE_MISSING_HMAC", "false").lower() == "true"

    if not hdr and not tolerate_missing:
        raise HTTPException(401, "Missing Shopify HMAC header")

    if hdr and not verify_shopify_hmac(raw, hdr, secret):
        raise HTTPException(401, "Invalid Shopify HMAC")

    shop_domain = _shop_domain_from_headers(request)
    if not shop_domain:
        raise HTTPException(400, "Missing shop domain header")

    try:
        payload = json.loads(raw.decode("utf-8") if raw else "{}")
    except Exception:
        payload = {}

    return shop_domain, payload


# -----------------------------------------------------
# Supabase service_role PostgREST + RPC (self-contained)
# -----------------------------------------------------

def _sb_headers() -> Dict[str, str]:
    key = _must_env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _sb_url(path: str) -> str:
    base = _must_env("SUPABASE_URL").rstrip("/")
    return f"{base}{path}"


def sb_select_one(table: str, filters: Dict[str, Any], columns: str = "*") -> Optional[Dict[str, Any]]:
    qs = "&".join([f"{k}=eq.{requests.utils.quote(str(v))}" for k, v in filters.items()])
    url = _sb_url(f"/rest/v1/{table}?select={requests.utils.quote(columns)}&{qs}&limit=1")
    r = requests.get(url, headers=_sb_headers(), timeout=25)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase select error ({table}): {r.text}")
    rows = r.json()
    return rows[0] if rows else None


def sb_upsert(table: str, row: Dict[str, Any], on_conflict: str) -> None:
    url = _sb_url(f"/rest/v1/{table}?on_conflict={requests.utils.quote(on_conflict)}")
    headers = _sb_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    r = requests.post(url, headers=headers, data=json.dumps(row), timeout=25)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase upsert error ({table}): {r.text}")


def sb_insert(table: str, row: Dict[str, Any]) -> None:
    url = _sb_url(f"/rest/v1/{table}")
    headers = _sb_headers()
    headers["Prefer"] = "return=minimal"
    r = requests.post(url, headers=headers, data=json.dumps(row), timeout=25)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase insert error ({table}): {r.text}")


def sb_patch(table: str, filters: Dict[str, Any], patch: Dict[str, Any]) -> None:
    qs = "&".join([f"{k}=eq.{requests.utils.quote(str(v))}" for k, v in filters.items()])
    url = _sb_url(f"/rest/v1/{table}?{qs}")
    headers = _sb_headers()
    headers["Prefer"] = "return=minimal"
    r = requests.patch(url, headers=headers, data=json.dumps(patch), timeout=25)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase patch error ({table}): {r.text}")


def sb_delete(table: str, filters: Dict[str, Any]) -> None:
    qs = "&".join([f"{k}=eq.{requests.utils.quote(str(v))}" for k, v in filters.items()])
    url = _sb_url(f"/rest/v1/{table}?{qs}")
    r = requests.delete(url, headers=_sb_headers(), timeout=25)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase delete error ({table}): {r.text}")


def sb_rpc_claim_job(merchant_id: str) -> Optional[Dict[str, Any]]:
    """
    Calls: POST /rest/v1/rpc/claim_shopify_backfill_job with { p_merchant_id: ... }
    Returns a single job row or None.
    """
    url = _sb_url("/rest/v1/rpc/claim_shopify_backfill_job")
    payload = {"p_merchant_id": merchant_id}
    r = requests.post(url, headers=_sb_headers(), data=json.dumps(payload), timeout=25)
    if r.status_code >= 400:
        raise HTTPException(500, f"Supabase RPC claim_shopify_backfill_job error: {r.text}")
    rows = r.json()
    return rows[0] if isinstance(rows, list) and rows else None


# -----------------------------------------------------
# Canonical resolver: shop_domain -> merchant_id
# -----------------------------------------------------

def resolve_merchant_id(shop_domain: str) -> Optional[str]:
    shop_domain = (shop_domain or "").strip().lower()
    if not shop_domain:
        return None
    m = sb_select_one("merchants", {"shop_domain": shop_domain}, columns="merchant_id,shop_domain")
    return (m or {}).get("merchant_id")


# -----------------------------------------------------
# Tokens
# -----------------------------------------------------

def get_shopify_access_token(shop_domain: str) -> Optional[str]:
    row = sb_select_one("shopify_tokens", {"shop_domain": shop_domain}, columns="shop_domain,access_token")
    token = (row or {}).get("access_token")
    return token if token else None


# -----------------------------------------------------
# Shopify Admin REST fetch helpers
# -----------------------------------------------------

def _shopify_api_version() -> str:
    return _env("SHOPIFY_API_VERSION", "2024-10")


def shopify_get(shop_domain: str, access_token: str, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple REST GET for Shopify Admin API.
    Example path: /orders.json, /customers.json, /products.json
    """
    ver = _shopify_api_version()
    base = f"https://{shop_domain}/admin/api/{ver}"
    url = f"{base}{path}"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code >= 400:
        raise HTTPException(502, f"Shopify API error {r.status_code}: {r.text}")
    return r.json() if r.text else {}


# -----------------------------------------------------
# Persistence helpers
# -----------------------------------------------------

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def persist_order(merchant_id: str, shop_domain: str, payload: Dict[str, Any]) -> None:
    order_id = payload.get("id")
    if not order_id:
        return
    row = {
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "order_id": str(order_id),
        "payload": payload,
        "updated_at": _now_iso(),
    }
    sb_upsert("shopify_orders", row, on_conflict="merchant_id,order_id")


def persist_customer(merchant_id: str, shop_domain: str, payload: Dict[str, Any]) -> None:
    customer_id = payload.get("id")
    if not customer_id:
        return
    row = {
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "customer_id": str(customer_id),
        "email": (payload.get("email") or "").strip().lower() or None,
        "payload": payload,
        "updated_at": _now_iso(),
    }
    sb_upsert("shopify_customers", row, on_conflict="merchant_id,customer_id")


def persist_product(merchant_id: str, shop_domain: str, payload: Dict[str, Any]) -> None:
    product_id = payload.get("id")
    if not product_id:
        return
    row = {
        "merchant_id": merchant_id,
        "shop_domain": shop_domain,
        "product_id": str(product_id),
        "payload": payload,
        "updated_at": _now_iso(),
    }
    sb_upsert("shopify_products", row, on_conflict="merchant_id,product_id")


# -----------------------------------------------------
# Secure worker gate
# -----------------------------------------------------

def require_worker_token(request: Request) -> None:
    expected = _must_env("BACKFILL_WORKER_TOKEN")
    got = (request.headers.get("X-Worker-Token") or "").strip()
    if not got or got != expected:
        raise HTTPException(401, "Missing or invalid X-Worker-Token")


# -----------------------------------------------------
# Routes: health/ping
# -----------------------------------------------------

@router.get("/ping")
def ping():
    return {"ok": True, "service": "shopify"}


# -----------------------------------------------------
# Routes: webhooks
# -----------------------------------------------------

@router.post("/webhooks/orders/create")
async def webhook_orders_create(request: Request):
    shop_domain, payload = await _handle_webhook(request)
    merchant_id = resolve_merchant_id(shop_domain)
    if not merchant_id:
        return {"ok": True, "ignored": True, "reason": "merchant_not_resolved", "shop_domain": shop_domain}
    persist_order(merchant_id, shop_domain, payload)
    return {"ok": True}


@router.post("/webhooks/orders/updated")
async def webhook_orders_updated(request: Request):
    shop_domain, payload = await _handle_webhook(request)
    merchant_id = resolve_merchant_id(shop_domain)
    if not merchant_id:
        return {"ok": True, "ignored": True, "reason": "merchant_not_resolved", "shop_domain": shop_domain}
    persist_order(merchant_id, shop_domain, payload)
    return {"ok": True}


@router.post("/webhooks/customers/create")
async def webhook_customers_create(request: Request):
    shop_domain, payload = await _handle_webhook(request)
    merchant_id = resolve_merchant_id(shop_domain)
    if not merchant_id:
        return {"ok": True, "ignored": True, "reason": "merchant_not_resolved", "shop_domain": shop_domain}
    persist_customer(merchant_id, shop_domain, payload)
    return {"ok": True}


@router.post("/webhooks/app/uninstalled")
async def webhook_app_uninstalled(request: Request):
    shop_domain, payload = await _handle_webhook(request)
    try:
        sb_delete("shopify_tokens", {"shop_domain": shop_domain})
    except Exception:
        pass
    return {"ok": True, "shop_domain": shop_domain}


# -----------------------------------------------------
# Step E: enqueue jobs
# -----------------------------------------------------

@router.post("/backfill/enqueue")
async def backfill_enqueue(request: Request, shop_domain: str, types: str = "orders,customers,products"):
    """
    Enqueue backfill jobs for a merchant.
    Requires worker token (we treat this as an admin-only action).
    """
    require_worker_token(request)

    shop_domain = (shop_domain or "").strip().lower()
    if not shop_domain:
        raise HTTPException(400, "Missing shop_domain")

    merchant_id = resolve_merchant_id(shop_domain)
    if not merchant_id:
        raise HTTPException(404, "Unable to resolve merchant identity")

    type_list = [t.strip().lower() for t in (types or "").split(",") if t.strip()]
    allowed = {"orders", "customers", "products"}
    type_list = [t for t in type_list if t in allowed]
    if not type_list:
        raise HTTPException(400, "No valid types provided")

    # Insert one job per type; dedupe by letting unique constraints handle repeats if you add them.
    for t in type_list:
        sb_insert(
            "shopify_backfill_jobs",
            {
                "merchant_id": merchant_id,
                "job_type": t,
                "status": "queued",
                "payload": {"cursor": None, "attempts": 0},
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            },
        )

    return {"ok": True, "merchant_id": merchant_id, "shop_domain": shop_domain, "enqueued": type_list}


# -----------------------------------------------------
# Step E: worker (process 1 job)
# -----------------------------------------------------

def _process_job(job: Dict[str, Any], shop_domain: str, merchant_id: str, token: str, max_items: int) -> Dict[str, Any]:
    job_id = job.get("job_id")
    job_type = (job.get("job_type") or "").strip().lower()
    payload = job.get("payload") or {}
    cursor = payload.get("cursor")  # can be "since_id" or ISO timestamp later
    attempts = int(payload.get("attempts") or 0)

    processed = 0

    try:
        if job_type == "orders":
            params: Dict[str, Any] = {"limit": min(max_items, 50), "status": "any", "order": "id asc"}
            if cursor:
                params["since_id"] = cursor
            data = shopify_get(shop_domain, token, "/orders.json", params=params)
            orders = data.get("orders") or []
            for o in orders:
                persist_order(merchant_id, shop_domain, o)
                processed += 1
            next_cursor = str(orders[-1]["id"]) if orders else None

        elif job_type == "customers":
            params = {"limit": min(max_items, 50), "order": "id asc"}
            if cursor:
                params["since_id"] = cursor
            data = shopify_get(shop_domain, token, "/customers.json", params=params)
            customers = data.get("customers") or []
            for c in customers:
                persist_customer(merchant_id, shop_domain, c)
                processed += 1
            next_cursor = str(customers[-1]["id"]) if customers else None

        elif job_type == "products":
            params = {"limit": min(max_items, 50), "order": "id asc"}
            if cursor:
                params["since_id"] = cursor
            data = shopify_get(shop_domain, token, "/products.json", params=params)
            products = data.get("products") or []
            for p in products:
                persist_product(merchant_id, shop_domain, p)
                processed += 1
            next_cursor = str(products[-1]["id"]) if products else None

        else:
            raise HTTPException(400, f"Unknown job_type: {job_type}")

        # Decide done vs continue
        if processed == 0:
            # nothing returned => done
            sb_patch("shopify_backfill_jobs", {"job_id": job_id}, {"status": "done", "updated_at": _now_iso()})
            return {"ok": True, "job_id": job_id, "job_type": job_type, "status": "done", "processed": 0}

        # continue: re-enqueue by setting back to queued with cursor
        sb_patch(
            "shopify_backfill_jobs",
            {"job_id": job_id},
            {
                "status": "queued",
                "payload": {"cursor": next_cursor, "attempts": attempts},
                "updated_at": _now_iso(),
            },
        )
        return {"ok": True, "job_id": job_id, "job_type": job_type, "status": "queued", "processed": processed, "next_cursor": next_cursor}

    except HTTPException as e:
        # retryable
        attempts += 1
        sb_patch(
            "shopify_backfill_jobs",
            {"job_id": job_id},
            {
                "status": "retry" if attempts < 5 else "failed",
                "payload": {"cursor": cursor, "attempts": attempts, "error": str(e.detail)},
                "updated_at": _now_iso(),
            },
        )
        raise


@router.post("/backfill/worker/once")
async def backfill_worker_once(
    request: Request,
    merchant_id: str,
    max_items: int = 50,
):
    """
    Claims ONE job for merchant_id and processes it.
    Call this from Render Cron Job every minute (or similar).
    Requires X-Worker-Token.
    """
    require_worker_token(request)

    merchant_id = (merchant_id or "").strip()
    if not merchant_id:
        raise HTTPException(400, "Missing merchant_id")

    # Resolve merchant shop_domain
    m = sb_select_one("merchants", {"merchant_id": merchant_id}, columns="merchant_id,shop_domain")
    if not m:
        raise HTTPException(404, "Merchant not found")

    shop_domain = (m.get("shop_domain") or "").strip().lower()
    if not shop_domain:
        raise HTTPException(500, "Merchant missing shop_domain")

    token = get_shopify_access_token(shop_domain)
    if not token:
        raise HTTPException(409, "Missing Shopify access token for this shop_domain")

    job = sb_rpc_claim_job(merchant_id)
    if not job:
        return {"ok": True, "claimed": False, "merchant_id": merchant_id, "shop_domain": shop_domain}

    # Process the claimed job
    result = _process_job(job, shop_domain, merchant_id, token, max_items=max(1, min(max_items, 250)))
    return {"ok": True, "claimed": True, "merchant_id": merchant_id, "shop_domain": shop_domain, "result": result}
