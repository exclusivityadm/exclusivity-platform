from typing import Any, Dict, Optional
from apps.backend.db import get_supabase

def _sb():
    client = get_supabase()
    if not client:
        raise RuntimeError("Supabase client not configured (missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY).")
    return client

def get_active_plan_key_for_merchant(merchant_id: str) -> str:
    """
    Returns active plan_key for merchant. Defaults to 'preview' if no assignment exists.
    """
    sb = _sb()
    res = (
        sb.table("merchant_plans")
        .select("plan_key,status,active_from,active_to")
        .eq("merchant_id", merchant_id)
        .eq("status", "active")
        .order("active_from", desc=True)
        .limit(1)
        .execute()
    )
    if res.data and len(res.data) > 0:
        return res.data[0].get("plan_key") or "preview"
    return "preview"

def get_plan(plan_key: str) -> Dict[str, Any]:
    sb = _sb()
    res = sb.table("plans").select("*").eq("plan_key", plan_key).limit(1).execute()
    if not res.data:
        return {"plan_key": plan_key, "name": plan_key.title(), "description": None, "is_active": True}
    return res.data[0]

def get_entitlements(plan_key: str) -> Dict[str, Any]:
    sb = _sb()
    res = sb.table("plan_entitlements").select("entitlement_key,enabled,meta").eq("plan_key", plan_key).execute()
    ent: Dict[str, Any] = {}
    for row in (res.data or []):
        ent[row["entitlement_key"]] = {"enabled": bool(row["enabled"]), "meta": row.get("meta") or {}}
    return ent

def assign_plan(merchant_id: str, plan_key: str) -> Dict[str, Any]:
    """
    Server-controlled assignment. Ends any existing active plan, inserts a new active one.
    """
    sb = _sb()

    # End current active assignments
    sb.table("merchant_plans").update({"status": "ended"}).eq("merchant_id", merchant_id).eq("status", "active").execute()

    ins = sb.table("merchant_plans").insert({
        "merchant_id": merchant_id,
        "plan_key": plan_key,
        "status": "active",
    }).execute()

    return {"ok": True, "inserted": ins.data}
