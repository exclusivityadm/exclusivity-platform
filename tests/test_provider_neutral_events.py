"""Offline contract tests. No database, credentials or paid service required."""

import unittest

from apps.backend.routes.services.integrations.normalized_events import (
    NormalizedCommerceEvent,
)


def event(**changes):
    defaults = {
        "merchant_id": "merchant-1",
        "source": "circahaus",
        "source_account_id": "creator-42",
        "source_event_id": "paid-order-101",
        "customer_ref": "member-local-789",
        "event_type": "order_paid",
        "occurred_at": "2026-11-11T12:00:00Z",
        "currency": "USD",
        "amount_minor": 2450,
    }
    defaults.update(changes)
    return NormalizedCommerceEvent(**defaults)


class ProviderNeutralEventContractTests(unittest.TestCase):
    def test_retry_is_deterministic(self):
        self.assertEqual(event().replay_key, event().replay_key)

    def test_source_tenant_and_account_isolation(self):
        key = event().replay_key
        self.assertNotEqual(key, event(merchant_id="merchant-2").replay_key)
        self.assertNotEqual(key, event(source="shopify").replay_key)
        self.assertNotEqual(key, event(source_account_id="shop-2").replay_key)
        self.assertNotEqual(key, event(source_event_id="paid-order-102").replay_key)
        self.assertNotEqual(key, event(event_type="refund_issued").replay_key)

    def test_money_never_uses_floats(self):
        for amount in (0, -3, 1.5, True):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                event(amount_minor=amount)

    def test_requires_authorized_source_and_event(self):
        with self.assertRaises(ValueError):
            event(source="unknown")
        with self.assertRaises(ValueError):
            event(event_type="unpaid_order")

    def test_requires_opaque_customer_and_valid_refs(self):
        for value in ("", "   ", "a" * 257):
            with self.subTest(value=value[:12]), self.assertRaises(ValueError):
                event(source_event_id=value)
        with self.assertRaises(ValueError):
            event(customer_ref="buyer@example.com")

    def test_requires_currency_and_timezone(self):
        for value in ("usd", "US", "USD1"):
            with self.subTest(currency=value), self.assertRaises(ValueError):
                event(currency=value)
        for value in ("2026-11-11T12:00:00", "yesterday"):
            with self.subTest(occurred_at=value), self.assertRaises(ValueError):
                event(occurred_at=value)

    def test_partial_refund_events_must_have_distinct_source_ids(self):
        first = event(event_type="refund_issued", source_event_id="refund-abc")
        second = event(event_type="refund_issued", source_event_id="refund-def")
        self.assertNotEqual(first.replay_key, second.replay_key)


if __name__ == "__main__":
    unittest.main()
