import logging
import time
from typing import Dict, Any
from fastapi import Request, Response

log = logging.getLogger("exclusivity.admin")

SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "x-api-key",
    "x-supabase-key",
}

def _mask_headers(headers: Dict[str, str]) -> Dict[str, str]:
    out = {}
    for k, v in headers.items():
        if k.lower() in SENSITIVE_HEADERS:
            out[k] = "***masked***"
        else:
            out[k] = v
    return out

async def log_request_response(request: Request, response: Response, start_time: float):
    duration_ms = int((time.time() - start_time) * 1000)

    entry: Dict[str, Any] = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
        "client": request.client.host if request.client else None,
        "headers": _mask_headers(dict(request.headers)),
    }

    log.info(entry)
