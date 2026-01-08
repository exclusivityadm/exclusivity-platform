# apps/backend/middleware/request_context.py
from __future__ import annotations

from fastapi import Request, Response
from typing import Callable, Awaitable, Optional
import time
import uuid

from apps.backend.core.context import RequestContext
from apps.backend.core.identity import resolve_identity_from_request
from apps.backend.core.feature_flags import compute_kill_switches


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    t0 = time.time()
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())

    identity = await resolve_identity_from_request(request)
    switches = await compute_kill_switches(identity.merchant_id)

    ctx = RequestContext(
        request_id=rid,
        merchant_id=identity.merchant_id,
        shop_domain=identity.shop_domain,
        actor_type=identity.actor_type,
        actor_id=identity.actor_id,
        auth_source=identity.auth_source,
        kill_switches=switches,
        started_at_ms=int(t0 * 1000),
    )

    request.state.ctx = ctx

    response = await call_next(request)
    response.headers["x-request-id"] = rid
    if ctx.merchant_id:
        response.headers["x-merchant-id"] = ctx.merchant_id
    return response
