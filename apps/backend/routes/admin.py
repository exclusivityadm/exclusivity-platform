from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict

from apps.backend.services.admin.overrides import (
    set_override,
    clear_override,
    list_overrides,
)
from apps.backend.services.admin.observability import system_snapshot

# ❌ NO prefix here — mounted in main.py
router = APIRouter(tags=["admin"])

class OverrideIn(BaseModel):
    key: str
    value: bool

@router.get("/overrides")
def get_overrides():
    return JSONResponse(content={"overrides": list_overrides()})

@router.post("/overrides")
def set_admin_override(inb: OverrideIn):
    set_override(inb.key, inb.value)
    return JSONResponse(content={"ok": True, "overrides": list_overrides()})

@router.delete("/overrides/{key}")
def clear_admin_override(key: str):
    clear_override(key)
    return JSONResponse(content={"ok": True, "overrides": list_overrides()})

@router.get("/observability")
def observability():
    return JSONResponse(content=system_snapshot())
