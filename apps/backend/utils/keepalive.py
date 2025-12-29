import os
import httpx
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger("keepalive")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

async def supabase_rest_keepalive():
    """
    Performs a REAL Supabase REST query that counts as activity.
    This prevents project pausing.
    """

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        log.warning("[KEEPALIVE] Supabase env vars missing")
        return

    url = f"{SUPABASE_URL}/rest/v1/rpc/now"

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(url, headers=headers, json={})
            if res.status_code < 400:
                log.info("[KEEPALIVE] Supabase REST activity OK")
            else:
                log.error(f"[KEEPALIVE] Supabase REST failed {res.status_code}")
    except Exception as e:
        log.error(f"[KEEPALIVE] Supabase error: {e}")


def start_keepalive(scheduler: AsyncIOScheduler, interval_seconds: int = 300):
    scheduler.add_job(
        supabase_rest_keepalive,
        "interval",
        seconds=interval_seconds,
        id="supabase_rest_keepalive",
        replace_existing=True,
    )
