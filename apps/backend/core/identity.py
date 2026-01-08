# apps/backend/core/identity.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from fastapi import Request

from apps.backend.routes.services.supabase_admin import select_one


@dataclass(frozen=True)
class ResolvedIdentity:
    merchant_id: Optional[str]
    shop_domain: Optional[str]
    actor_type: str     # "merchant" | "admin" | "internal" | "unknown"
    actor_id: Optional[str]
    auth_source: str    # "shopify" | "admin" | "internal" | "none"


async def resolve_identity_from_request(request: Request) -> ResolvedIdentity:
    """
    Canonical identity sources (highest → lowest):
      1) x-merchant-id (server-issued, internal)
      2) shop query param (install/onboarding)
      3) x-shop-domain header
      4) none
    """
    # Admin/internal future hooks
    internal_key = (request.headers.get("x-internal-key") or "").strip()
    admin_key = (request.headers.get("x-admin-key") or "").strip()

    if internal_key:
        return ResolvedIdentity(
            merchant_id=None,
            shop_domain=None,
            actor_type="internal",
            actor_id="internal",
            auth_source="internal",
        )

    if admin_key:
        return ResolvedIdentity(
            merchant_id=None,
            shop_domain=None,
            actor_type="admin",
            actor_id="admin",
            auth_source="admin",
        )

    merchant_id = (request.headers.get("x-merchant-id") or "").strip() or None
    if merchant_id:
        # If merchant_id provided, try to fetch shop_domain for context
        m = select_one("merchants", {"merchant_id": merchant_id}, columns="merchant_id,shop_domain")
        return ResolvedIdentity(
            merchant_id=m.get("merchant_id") if m else merchant_id,
            shop_domain=m.get("shop_domain") if m else None,
            actor_type="merchant",
            actor_id=m.get("merchant_id") if m else merchant_id,
            auth_source="internal",
        )

    shop = (request.query_params.get("shop") or "").strip().lower() or None
    if not shop:
        shop = (request.headers.get("x-shop-domain") or "").strip().lower() or None

    if shop:
        m = select_one("merchants", {"shop_domain": shop}, columns="merchant_id,shop_domain")
        if m and m.get("merchant_id"):
            return ResolvedIdentity(
                merchant_id=m.get("merchant_id"),
                shop_domain=m.get("shop_domain") or shop,
                actor_type="merchant",
                actor_id=m.get("merchant_id"),
                auth_source="shopify",
            )
        return ResolvedIdentity(
            merchant_id=None,
            shop_domain=shop,
            actor_type="merchant",
            actor_id=None,
            auth_source="shopify",
        )

    return ResolvedIdentity(
        merchant_id=None,
        shop_domain=None,
        actor_type="unknown",
        actor_id=None,
        auth_source="none",
    )
