# apps/backend/services/replay_guard.py
# =====================================================
# Replay Protection — Drop F
# =====================================================

import time
import hashlib

def action_fingerprint(action: dict) -> str:
    raw = repr(sorted(action.items())).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

_seen: dict[str, float] = {}

def is_replay(fp: str, window_seconds: int = 60) -> bool:
    now = time.time()
    last = _seen.get(fp)
    if last and now - last < window_seconds:
        return True
    _seen[fp] = now
    return False
