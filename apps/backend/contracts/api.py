# apps/backend/contracts/api.py
from typing import Any, Dict, Optional, TypedDict


class ApiOk(TypedDict):
    ok: bool
    data: Any


class ApiError(TypedDict, total=False):
    ok: bool
    error: str
    code: str
    details: Any


def api_ok(data: Any) -> ApiOk:
    return {
        "ok": True,
        "data": data,
    }


def api_error(
    error: str,
    code: str = "unknown_error",
    details: Optional[Any] = None,
) -> ApiError:
    payload: ApiError = {
        "ok": False,
        "error": error,
        "code": code,
    }
    if details is not None:
        payload["details"] = details
    return payload
