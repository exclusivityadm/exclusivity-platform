# apps/backend/services/merchant/service.py

from typing import Dict, Any
import os
import logging
from supabase import create_client, Client

log = logging.getLogger("uvicorn")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Supabase env vars missing")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def normalize_shop(shop: str) -> str:
    return (
        shop.strip()
        .lower()
        .replace("https://", "")
        .replace("http://", "")
        .rstrip("/")
    )


def ok(data: Any) -> Dict[str, Any]:
    return {"ok": True, "data": data}


def err(message: str, details: Any = None) -> Dict[str, Any]:
    payload = {"ok": False, "error": message}
    if details is not None:
        payload["details"] = details
    return payload


async def resolve_or_create_merchant(shop: str) -> Dict[str, Any]:
    if not shop:
        return err("Missing shop parameter")

    shop = normalize_shop(shop)

    try:
        # 1️⃣ Lookup
        res = (
            supabase
            .table("merchants")
            .select("*")
            .eq("shop_domain", shop)
            .limit(1)
            .execute()
        )

        if res.data:
            merchant = res.data[0]
            return ok({
                "merchant_id": merchant["id"],
                "shop_domain": merchant["shop_domain"],
                "created": False
            })

        # 2️⃣ Create
        insert = (
            supabase
            .table("merchants")
            .insert({
                "shop_domain": shop,
                "status": "onboarding",
            })
            .execute()
        )

        merchant = insert.data[0]

        return ok({
            "merchant_id": merchant["id"],
            "shop_domain": merchant["shop_domain"],
            "created": True
        })

    except Exception as e:
        log.exception("Merchant resolution failed")
        return err("Merchant resolution failed", str(e))
