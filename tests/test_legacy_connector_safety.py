"""Offline regression checks for legacy connector fail-closed behavior."""

import unittest

from apps.backend.services.shopify_backfill import (
    LEGACY_BACKFILL_BLOCK_REASON,
    enqueue_backfill,
    run_backfill_once,
)


class LegacyConnectorSafetyTests(unittest.TestCase):
    def test_backfill_cannot_touch_legacy_wallet(self):
        result = run_backfill_once("merchant-1")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["error_code"], "LEGACY_SHOPIFY_BACKFILL_DISABLED")
        self.assertIn("immutable loyalty ledger", result["error"])

    def test_enqueue_rejects_implicit_migration(self):
        with self.assertRaisesRegex(RuntimeError, "Historical Shopify backfill"):
            enqueue_backfill("merchant-1", "shop.myshopify.com")


if __name__ == "__main__":
    unittest.main()
