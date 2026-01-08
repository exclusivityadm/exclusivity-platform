# apps/backend/services/execution/loyalty.py
# =====================================================
# Loyalty Execution Bridge (FINAL)
# =====================================================

from typing import Dict, Any
import requests
import os

def execute_award_loyalty(merchant_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes loyalty award via internal worker route.
    """

    worker_token = os.getenv("BACKFILL_WORKER_TOKEN")
    api_url = os.getenv("INTERNAL_API_URL")

    if not worker_token or not api_url:
        raise RuntimeError("Missing worker configuration")

    resp = requests.post(
        f"{api_url}/loyalty/award-from-orders",
        headers={"X-Worker-Token": worker_token},
        params={
            "merchant_id": merchant_id,
            "limit": action.get("limit", 100),
        },
        timeout=30,
    )

    if resp.status_code >= 400:
        raise RuntimeError(f"Loyalty execution failed: {resp.text}")

    return resp.json()
