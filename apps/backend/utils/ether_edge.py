from fastapi import Request
import os
import hashlib


class EtherEdgeError(Exception):
    def __init__(self, message: str, status_code: int = 403):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def enforce_ether_headers(request: Request):
    """
    Enforces Ether trust headers for internal-only routes.
    Explicit opt-in. Never global.
    """

    internal_token = request.headers.get("X-ETHER-INTERNAL-TOKEN")
    source = request.headers.get("X-ETHER-SOURCE")

    if not internal_token or not source:
        raise EtherEdgeError("Missing Ether headers")

    expected = os.getenv("ETHER_INTERNAL_TOKEN")
    if not expected:
        raise EtherEdgeError("Ether internal token not configured", 500)

    if internal_token != expected:
        raise EtherEdgeError("Invalid Ether internal token")

    idem = request.headers.get("Idempotency-Key")
    if idem:
        request.state.idempotency_key = hashlib.sha256(idem.encode()).hexdigest()
    else:
        request.state.idempotency_key = None

    request.state.ether_source = source
