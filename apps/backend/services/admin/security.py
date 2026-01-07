# apps/backend/services/admin/security.py
# =====================================================
# Exclusivity Backend — Step 19 Security Layer (HMAC + Guardrails)
#
# Goals:
# - Provide a canonical HMAC verification mechanism for sensitive endpoints
# - Prevent replay attacks (timestamp + nonce)
# - Keep it simple: env-driven, no external deps required
#
# How to use:
#   from apps.backend.services.admin.security import require_hmac
#
#   @router.post("/some/sensitive")
#   def handler(..., _auth=Depends(require_hmac("SCOPE_NAME"))):
#       ...
#
# Headers expected:
#   X-Excl-Timestamp: unix epoch seconds (string)
#   X-Excl-Nonce: random nonce (string)
#   X-Excl-Signature: hex sha256 HMAC of canonical string
#
# Canonical string:
#   {METHOD}\n{PATH}\n{TIMESTAMP}\n{NONCE}\n{BODY_SHA256_HEX}
#
# Where:
# - PATH must be the raw request.url.path (no domain)
# - BODY_SHA256_HEX is sha256 of request body bytes (empty body allowed)
#
# Env vars:
#   EXCL_HMAC_SECRET              (required for enforcement)
#   EXCL_HMAC_ENFORCE=true|false  (default true)
#   EXCL_HMAC_MAX_SKEW_SECONDS    (default 300)
#   EXCL_HMAC_NONCE_TTL_SECONDS   (default 600)
#
# Notes:
# - Nonce cache is in-memory (fine for single instance / basic)
# - If you scale horizontally, swap nonce store to Redis later
# =====================================================

from __future__ import annotations

import os
import time
import hmac
import hashlib
import secrets
from typing import Callable, Optional, Dict
from fastapi import Request, HTTPException, Depends

# -----------------------------
# In-memory nonce cache
# nonce -> expires_at
# -----------------------------
_NONCE_CACHE: Dict[str, int] = {}


def _now() -> int:
    return int(time.time())


def _env_bool(name: str, default: str = "true") -> bool:
    return (os.getenv(name, default) or "").strip().lower() == "true"


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name, str(default)) or "").strip()
    try:
        return int(raw)
    except Exception:
        return default


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean_nonce_cache(now: int) -> None:
    # Remove expired nonces
    expired = [n for n, exp in _NONCE_CACHE.items() if exp <= now]
    for n in expired:
        _NONCE_CACHE.pop(n, None)


def _consume_nonce(nonce: str, ttl_seconds: int) -> None:
    """
    Enforce single-use nonce (basic replay protection).
    """
    now = _now()
    _clean_nonce_cache(now)

    if not nonce or len(nonce) < 8:
        raise HTTPException(status_code=401, detail="Invalid nonce")

    if nonce in _NONCE_CACHE:
        raise HTTPException(status_code=401, detail="Replay detected (nonce reused)")

    _NONCE_CACHE[nonce] = now + ttl_seconds


async def _canonical_string(request: Request, timestamp: str, nonce: str) -> str:
    body = await request.body()
    body_hash = _sha256_hex(body or b"")
    method = (request.method or "GET").upper()
    path = request.url.path  # raw path only
    return f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"


def _compute_sig(secret: str, msg: str) -> str:
    return hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()


def _constant_time_equal(a: str, b: str) -> bool:
    try:
        return hmac.compare_digest(a, b)
    except Exception:
        return False


def generate_hmac_headers(
    method: str,
    path: str,
    body_bytes: bytes,
    secret: str,
    timestamp: Optional[int] = None,
    nonce: Optional[str] = None,
) -> Dict[str, str]:
    """
    Helper for internal tools/tests to generate headers for a request.
    (Not used by the API automatically.)
    """
    ts = str(timestamp or _now())
    nn = nonce or secrets.token_hex(16)
    body_hash = _sha256_hex(body_bytes or b"")
    canonical = f"{method.upper()}\n{path}\n{ts}\n{nn}\n{body_hash}"
    sig = _compute_sig(secret, canonical)
    return {
        "X-Excl-Timestamp": ts,
        "X-Excl-Nonce": nn,
        "X-Excl-Signature": sig,
    }


def require_hmac(scope: str = "default") -> Callable:
    """
    FastAPI dependency that enforces HMAC if EXCL_HMAC_ENFORCE is true.
    """
    enforce = _env_bool("EXCL_HMAC_ENFORCE", "true")
    secret = (os.getenv("EXCL_HMAC_SECRET") or "").strip()

    max_skew = _env_int("EXCL_HMAC_MAX_SKEW_SECONDS", 300)
    nonce_ttl = _env_int("EXCL_HMAC_NONCE_TTL_SECONDS", 600)

    async def _dep(request: Request):
        if not enforce:
            return {"ok": True, "enforced": False, "scope": scope}

        if not secret:
            raise HTTPException(
                status_code=500,
                detail="Server misconfigured: EXCL_HMAC_SECRET missing",
            )

        ts = (request.headers.get("X-Excl-Timestamp") or "").strip()
        nonce = (request.headers.get("X-Excl-Nonce") or "").strip()
        sig = (request.headers.get("X-Excl-Signature") or "").strip()

        if not ts or not nonce or not sig:
            raise HTTPException(status_code=401, detail="Missing HMAC headers")

        # Timestamp skew check
        try:
            ts_int = int(ts)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid timestamp")

        now = _now()
        if abs(now - ts_int) > max_skew:
            raise HTTPException(status_code=401, detail="Timestamp skew too large")

        # Nonce replay protection
        _consume_nonce(nonce, ttl_seconds=nonce_ttl)

        # Signature verification
        canonical = await _canonical_string(request, ts, nonce)
        expected = _compute_sig(secret, canonical)

        if not _constant_time_equal(expected, sig):
            raise HTTPException(status_code=401, detail="Invalid signature")

        return {"ok": True, "enforced": True, "scope": scope}

    return Depends(_dep)
