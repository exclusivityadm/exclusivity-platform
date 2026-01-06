import json
import os
import socket
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from apps.backend.routes.services.supabase_admin import (
    insert_one,
    select_one,
    upsert_one,
    update_where,
    rpc,
)

BLOCKCHAIN_MODE = os.getenv("BLOCKCHAIN_MODE", "internal")  # internal|provider
WORKER_ID = os.getenv("WORKER_ID", "") or socket.gethostname()

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def ensure_customer_wallet(merchant_id: str, customer_id: str) -> Dict[str, Any]:
    """
    Ensures a customer_wallet exists. In 'internal' mode we mark it ready immediately.
    """
    existing = select_one("customer_wallets", {"merchant_id": merchant_id, "customer_id": customer_id})
    if existing:
        return existing

    wallet = insert_one("customer_wallets", {
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "provider": "internal" if BLOCKCHAIN_MODE == "internal" else "custodial_provider",
        "wallet_ref": f"internal:{merchant_id}:{customer_id}" if BLOCKCHAIN_MODE == "internal" else None,
        "status": "ready" if BLOCKCHAIN_MODE == "internal" else "pending",
    })
    return wallet

def enqueue_mint_job(
    *,
    merchant_id: str,
    customer_id: str,
    job_type: str,
    source: str,
    source_ref: Optional[str],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Enqueues a mint job idempotently (unique on merchant_id, job_type, source, source_ref).
    If source_ref is None, it will not be uniquely deduped.
    """
    row = {
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "job_type": job_type,
        "source": source,
        "source_ref": source_ref,
        "payload": payload or {},
        "status": "queued",
    }

    # If source_ref provided, dedupe via upsert-like behavior:
    if source_ref:
        try:
            # PostgREST upsert requires conflict cols; we don't have a single constraint name, but we do have a unique index.
            # We'll emulate idempotency by checking first.
            existing = select_one("mint_jobs", {
                "merchant_id": merchant_id,
                "job_type": job_type,
                "source": source,
                "source_ref": source_ref,
            })
            if existing:
                return existing
        except Exception:
            pass

    return insert_one("mint_jobs", row)

def _log_event(mint_job_id: str, merchant_id: str, event: str, details: Optional[str] = None) -> None:
    insert_one("mint_job_events", {
        "mint_job_id": mint_job_id,
        "merchant_id": merchant_id,
        "event": event,
        "details": details,
    })

def _schedule_retry(mint_job_id: str, delay_seconds: int, attempts_next: int, error_last: str) -> None:
    # Store run_after as ISO string; Supabase accepts timestamptz strings
    run_after = datetime.now(timezone.utc).timestamp() + delay_seconds
    # Convert epoch to ISO
    run_after_iso = datetime.fromtimestamp(run_after, tz=timezone.utc).isoformat()
    update_where("mint_jobs", {"id": mint_job_id}, {
        "status": "retrying",
        "attempts": attempts_next,
        "run_after": run_after_iso,
        "error_last": error_last,
    })

def _internal_execute(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Internal mode: mark completed with a simulated tx reference.
    """
    payload = job.get("payload") or {}
    simulated_tx = f"simtx:{job['id']}"
    return {"tx_ref": simulated_tx, "payload": payload}

def process_one_mint_job() -> Dict[str, Any]:
    """
    Worker tick: claim one mint job and process it.
    """
    claimed = rpc("claim_mint_job", {"worker_id": WORKER_ID})
    if not claimed:
        return {"ok": True, "job": None}

    job = claimed[0]
    mint_job_id = job["id"]
    merchant_id = job["merchant_id"]
    customer_id = job["customer_id"]
    attempts_next = int(job.get("attempts") or 0) + 1

    _log_event(mint_job_id, merchant_id, "started", f"worker={WORKER_ID}")

    try:
        ensure_customer_wallet(merchant_id, customer_id)

        if BLOCKCHAIN_MODE == "internal":
            result = _internal_execute(job)
        else:
            # Provider mode placeholder — keep engine complete but not bound to a vendor yet.
            # When you choose provider, we implement here without touching other files.
            raise RuntimeError("BLOCKCHAIN_MODE=provider not configured")

        update_where("mint_jobs", {"id": mint_job_id}, {
            "status": "completed",
            "attempts": attempts_next,
            "error_last": None,
        })
        _log_event(mint_job_id, merchant_id, "completed", json.dumps(result)[:900])

        return {"ok": True, "job": mint_job_id, "status": "completed", "result": result}

    except Exception as e:
        err = str(e)
        # Exponential-ish backoff capped
        delay = min(300, 15 * attempts_next)
        _log_event(mint_job_id, merchant_id, "retry_scheduled", f"{err} (delay={delay}s)")
        _schedule_retry(mint_job_id, delay_seconds=delay, attempts_next=attempts_next, error_last=err)
        return {"ok": False, "job": mint_job_id, "status": "retrying", "error": err}
