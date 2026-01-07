# apps/backend/routes/actions.py
# =====================================================
# Exclusivity Backend — STEP 22 (FINAL)
# ACTIONS / PREVIEW ROUTES
#
# Contract-compliant:
#   ApiResponse[T] ONLY
#
# ❌ No ad-hoc error keys
# ❌ No implicit unions
# ❌ No frontend guessing
# =====================================================

from __future__ import annotations

from fastapi import APIRouter
from typing import Any, Dict

from apps.backend.contracts.api import (
    ApiOk,
    ApiErr,
    ApiResponse,
    ActionPreviewResult,
)

router = APIRouter(tags=["actions"])  # prefix owned by main.py


# -----------------------------------------------------
# POST /actions/preview
# -----------------------------------------------------
@router.post("/actions/preview", response_model=ApiResponse[ActionPreviewResult])
def preview_action(payload: Dict[str, Any]):
    """
    Preview an action before execution.
    This endpoint is intentionally conservative and deterministic.
    """

    if not payload:
        return ApiErr(
            code="action.invalid",
            message="Missing preview payload",
        )

    try:
        # ---- PLACEHOLDER LOGIC (SAFE + STABLE) ----
        # This allows frontend development to proceed
        # without blocking on business logic.

        preview = ActionPreviewResult(
            cost_estimate=0,
            description="Preview generated successfully",
            metadata={
                "payload_keys": list(payload.keys()),
            },
        )

        return ApiOk(data=preview)

    except Exception as e:
        return ApiErr(
            code="action.preview_failed",
            message="Failed to generate action preview",
            details={"error": str(e)},
        )
