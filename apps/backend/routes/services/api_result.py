# apps/backend/routes/services/api_result.py
from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict, Union


class ApiOk(TypedDict):
    ok: bool
    data: Any


class ApiErr(TypedDict, total=False):
    ok: bool
    error: str
    details: Any


ApiResult = Union[ApiOk, ApiErr]


def ok(data: Any) -> ApiOk:
    return {"ok": True, "data": data}


def err(error: str, details: Optional[Any] = None) -> ApiErr:
    out: ApiErr = {"ok": False, "error": error}
    if details is not None:
        out["details"] = details
    return out


def coerce_error_message(e: Exception) -> str:
    return str(e) or e.__class__.__name__
