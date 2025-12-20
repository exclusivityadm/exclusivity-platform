from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import uuid

from apps.backend.db import get_supabase


@dataclass
class MerchantIdentity:
    merchant_id: str          # canonical UUID string
    provider: str             # "shopify"
    shop_domain: str          # "example.myshopify.com"


def _new_merchant_id() -> str:
    return str(uuid.uuid4())


def resolve_merchant_id_by_shop_domain(shop_domain: str, provider: str = "shopify") -> Optional[str]:
    """
    Looks up existing canonical merchant_id for a given shop domain + provider.
    Returns merchant_id (UUID as string) or None.
    """
    sb = get_supabase()
    if not sb:
        return None

    r = (
        sb.table("merchant_integrations")
        .select("merchant_id")
        .eq("provider", provider)
        .eq("shop_domain", shop_domain.lower().strip())
        .limit(1)
        .execute()
    )
    if not r.data:
        return None
    mid = (r.data[0] or {}).get("merchant_id")
    return str(mid) if mid else None


def get_or_create_merchant_identity_for_shop(shop_domain: str, provider: str = "shopify") -> MerchantIdentity:
    """
    Canonical identity creation rule:
    - If we have an integration mapping, reuse merchant_id.
    - Else generate a new UUID merchant_id (Exclusivity-owned).
    """
    shop_domain = shop_domain.lower().strip()
    existing = resolve_merchant_id_by_shop_domain(shop_domain, provider=provider)
    if existing:
        return MerchantIdentity(merchant_id=existing, provider=provider, shop_domain=shop_domain)

    return MerchantIdentity(merchant_id=_new_merchant_id(), provider=provider, shop_domain=shop_domain)


def upsert_integration(
    merchant_id: str,
    provider: str,
    shop_domain: str,
    access_token: str,
    scopes: str = "",
) -> Dict[str, Any]:
    """
    Upserts merchant_integrations mapping.
    merchant_id is the canonical UUID string (stored as text).
    """
    sb = get_supabase()
    if not sb:
        return {"ok": False, "error": "Supabase not configured"}

    shop_domain = shop_domain.lower().strip()

    sb.table("merchant_integrations").upsert(
        {
            "merchant_id": merchant_id,
            "provider": provider,
            "shop_domain": shop_domain,
            "access_token": access_token,
            "scopes": scopes,
        },
        on_conflict="merchant_id,provider",
    ).execute()

    return {"ok": True, "merchant_id": merchant_id, "provider": provider, "shop_domain": shop_domain}
