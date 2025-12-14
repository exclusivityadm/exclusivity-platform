from __future__ import annotations
from typing import Dict, Any

from apps.backend.health_checks.loyalty_healthcheck import loyalty_healthcheck
from apps.backend.repositories.loyalty_repository import LoyaltyRepository


async def run_keepalive(repo: LoyaltyRepository) -> Dict[str, Any]:
    return {
        "keepalive": True,
        "health": await loyalty_healthcheck(repo),
    }
