from typing import Dict

# In-memory overrides (intentionally ephemeral)
# These are NOT silent and NOT persisted.
_OVERRIDES: Dict[str, bool] = {}

def set_override(key: str, value: bool):
    _OVERRIDES[key] = bool(value)

def clear_override(key: str):
    _OVERRIDES.pop(key, None)

def get_override(key: str, default: bool = False) -> bool:
    return _OVERRIDES.get(key, default)

def list_overrides() -> Dict[str, bool]:
    return dict(_OVERRIDES)
