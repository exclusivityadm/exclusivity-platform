# apps/backend/services/rate_guard.py
# =====================================================
# Rate Guard — Drop F
# =====================================================

import time

_bucket: dict[str, list[float]] = {}

def allow_action(merchant_id: str, limit: int = 20, per_seconds: int = 60) -> bool:
    now = time.time()
    window = _bucket.setdefault(merchant_id, [])
    window[:] = [t for t in window if now - t < per_seconds]

    if len(window) >= limit:
        return False

    window.append(now)
    return True
