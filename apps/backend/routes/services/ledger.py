from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class LedgerEvent:
    """
    Canonical ledger event model.

    This file exists ONLY to provide a stable import target
    for loyalty + health modules.

    No business logic belongs here.
    """

    event_id: str
    member_ref: str
    event_type: str
    points_delta: int

    idempotency_key: Optional[str] = None
    related_ref: Optional[str] = None
    related_line_ref: Optional[str] = None
    created_at: Optional[str] = None
    reason: Optional[str] = None
    meta: Dict[str, Any] | None = None
