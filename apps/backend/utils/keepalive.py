# apps/backend/utils/keepalive.py

import os
import httpx
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger("keepalive")

# --------------------------------------------------------
# Supabase REST Keepalive (REAL ACTIVITY)
# --------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Optional non-Supabase keepalives (Render / Vercel)
OPTIONAL_URLS = [
    os.getenv("KEEPALIVE_RENDER_URL"),
    os.getenv("KEEPALIVE_VERCEL_URL"),
    os.getenv("KEEPALIVE_CUSTOM_1"),
    os.getenv("KEEPALIVE_CUSTOM_2"),
]


async def supabase_rest_ping():
    """
    Performs a real Supabase REST query that counts as activity.
    This is the ONLY backend keepalive Supabase reliably recognizes.
    """

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        log.warning("[KEEPALIVE] Supabase env vars missing — skipping Supabase ping")
        return

    url = f"{SUPABASE_URL}/rest/v1/"

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Lightweight REST call — no table dependency
            res = await client.get(url, headers=headers)
            if res.status_code < 400:
                log.info("[KEEPALIVE] Supabase REST ping OK")
            else:
                log.warning(f"[KEEPALIVE] Supabase REST ping failed ({res.status_code})")
    except Exception as e:
        log.error(f"[KEEPALIVE] Supabase REST error: {e}")


async def optional_http_pings():
    """
    Keeps Render / Vercel warm.
    NOT counted by Supabase — secondary only.
    """
    urls = [u for u in OPTIONAL_URLS if u]
    if not urls:
        return

    async with httpx.AsyncClient(timeout=10) as client:
        for url in urls:
            try:
                await client.get(url)
            except Exception:
                pass


def start_keepalive_tasks(scheduler: AsyncIOScheduler, interval_seconds: int = 300):
    """
    Starts real Supabase keepalive + optional platform pings.
    """

    scheduler.add_job(
        supabase_rest_ping,
        "interval",
        seconds=interval_seconds,
        id="supabase_rest_keepalive",
        replace_existing=True,
    )

    scheduler.add_job(
        optional_http_pings,
        "interval",
        seconds=interval_seconds,
        id="optional_http_keepalive",
        replace_existing=True,
    )

    log.info(
        f"[KEEPALIVE] Scheduler started — interval {interval_seconds}s "
        "(Supabase REST + optional HTTP)"
    )
