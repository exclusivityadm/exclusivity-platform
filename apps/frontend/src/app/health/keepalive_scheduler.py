"""
Keepalive Scheduler
===================

Purpose:
- Prevent Supabase from auto-pausing
- Safe, low-cost periodic activity
- Can be called by:
  - Render cron
  - Vercel cron
  - External uptime monitor
"""

from __future__ import annotations
from typing import Dict, Any

from app.repositories.loyalty_repository import LoyaltyRepository
from app.health.loyalty_healthcheck import loyalty_healthcheck


async def run_keepalive(repo: LoyaltyRepository) -> Dict[str, Any]:
    """
    Execute a minimal, safe keepalive cycle.
    """
    health = await loyalty_healthcheck(repo)
    return {
        "keepalive": True,
        "health": health,
    }
