from __future__ import annotations

from typing import Any, Dict


LEGACY_BACKFILL_BLOCK_REASON = (
    "Historical Shopify backfill is intentionally unavailable pending "
    "reconciliation of the immutable loyalty ledger, wallet schemas, "
    "currency handling, and merchant-scoped authorizations."
)


def enqueue_backfill(merchant_id: str, shop_domain: str) -> None:
    """Legacy interface: safely decline to create backfill jobs.

    OAuth integration must not silently start a destructive migration.
    The new provider-neutral historical import must replace this path.
    """
    raise RuntimeError(LEGACY_BACKFILL_BLOCK_REASON)


def run_backfill_once(merchant_id: str) -> Dict[str, Any]:
    """Fail closed until an idempotent, audited importer replaces this path.

    Prior implementation mixed incompatible wallet schema columns, wrote
    floating-point balances, deleted historical ledger entries, and silently
    skipped failed RPC recomputations. It is preserved in Git history, not run.
    """
    return {
        "ok": False,
        "merchant_id": merchant_id,
        "status": "blocked",
        "error_code": "LEGACY_SHOPIFY_BACKFILL_DISABLED",
        "error": LEGACY_BACKFILL_BLOCK_REASON,
    }
