# apps/backend/utils/keepalive.py

import os
import httpx
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger("keepalive")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

OPTIONAL_URLS = [
    os.getenv("KEEPALIVE_RENDER_URL"),
    os.getenv("KEEPALIVE_VERCEL_URL"),
    os.getenv("KEEPALIVE_CUSTOM_1"),
    os.getenv("KEEPALIVE_CUSTOM_2"),
]


async def supabase_rest_ping():
    """
    REAL Supabase activity.
    Executes an actual PostgREST query that Supabase counts.
    """

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        log.warning("[KEEPALIVE] Supabase env vars missing")
        return

    # Use a real table + SELECT (read-only, minimal cost)
    url = f"{SUPABASE_URL}/rest/v1/customer_wallets?select=id&limit=1"

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, headers=headers)
            if res.status_code < 400:
                log.info("[KEEPALIVE] Supabase DB keepalive OK")
            else:
                log.warning(
                    f"[KEEPALIVE] Supabase DB keepalive failed ({res.status_code})"
                )
    except Exception as e:
        log.error(f"[KEEPALIVE] Supabase DB keepalive error: {e}")


async def optional_http_pings():
    urls = [u for u in OPTIONAL_URLS if u]
    if not urls:
        return

    async with httpx.AsyncClient(timeout=10) as client:
        for url in urls:
            try:
                await client.get(url)
            except Exception:
                pass


def start_keepalive_tasks(
    scheduler: AsyncIOScheduler,
    interval_seconds: int = 300,
):
    scheduler.add_job(
        supabase_rest_ping,
        "interval",
        seconds=interval_seconds,
        id="supabase_db_keepalive",
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
        f"[KEEPALIVE] Started — interval {interval_seconds}s "
        "(Supabase DB + optional HTTP)"
    )
