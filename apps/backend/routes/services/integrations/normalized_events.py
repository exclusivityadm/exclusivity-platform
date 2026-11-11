"""Provider-neutral commerce event boundary for Exclusivity.

Pure validation and replay identity only. This module does not award points,
mutate a database, call Circa Haus/Shopify APIs, or process payments.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import re

SUPPORTED_SOURCES = frozenset({"circahaus", "shopify", "external"})
SUPPORTED_EVENTS = frozenset({"order_paid", "refund_issued"})
_CURRENCY = re.compile(r"^[A-Z]{3}$")


def _required_ref(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    if len(value) > 256 or any(ord(c) < 32 for c in value):
        raise ValueError(f"{name} must be at most 256 printable characters")


@dataclass(frozen=True)
class NormalizedCommerceEvent:
    """An immutable, merchant-scoped fact from an authorized source adapter.

    `amount_minor` is a positive integer in the source currency's *actual*
    minor units; no assumption that every currency has two decimal places.
    Refund amounts are positive facts, not negative ledger entries.
    The loyalty policy decides whether/how many points to grant or reverse.
    `customer_ref` must be an opaque *merchant-scoped* reference, not an email.
    """

    merchant_id: str
    source: str
    source_account_id: str
    source_event_id: str
    customer_ref: str
    event_type: str
    occurred_at: str
    currency: str
    amount_minor: int

    def __post_init__(self) -> None:
        for name in (
            "merchant_id", "source_account_id", "source_event_id", "customer_ref"
        ):
            _required_ref(name, getattr(self, name))
        if self.source not in SUPPORTED_SOURCES:
            raise ValueError("source must be an approved adapter")
        if self.event_type not in SUPPORTED_EVENTS:
            raise ValueError("event_type must describe a supported final event")
        if "@" in self.customer_ref:
            raise ValueError("customer_ref must be opaque, never an email address")
        if not isinstance(self.currency, str) or not _CURRENCY.fullmatch(self.currency):
            raise ValueError("currency must be an uppercase ISO 4217 code")
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int) or self.amount_minor <= 0:
            raise ValueError("amount_minor must be a positive integer")
        if not isinstance(self.occurred_at, str):
            raise ValueError("occurred_at must be an RFC3339 timestamp with timezone")
        try:
            timestamp = datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("occurred_at must be an RFC3339 timestamp with timezone") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")

    @property
    def replay_key(self) -> str:
        """Stable deduplication identity including tenant, provider and event kind.

        The source adapter must use a stable, unique source_event_id for each
        paid order and each distinct refund, including partial refunds.
        """
        identity = {
            "version": 1,
            "merchant_id": self.merchant_id,
            "source": self.source,
            "source_account_id": self.source_account_id,
            "source_event_id": self.source_event_id,
            "event_type": self.event_type,
        }
        canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        return "exc-v1-" + sha256(canonical.encode("utf-8")).hexdigest()
