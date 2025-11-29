import os
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --------------------------------------------------------
# Multi-provider Keepalive Ping Scheduler
#   - Supabase
#   - Render backend
#   - Vercel frontend
# --------------------------------------------------------

def schedule_keepalive(scheduler: AsyncIOScheduler, interval_seconds: int = 300):
    """
    Pings all configured keepalive URLs every X seconds.
    Completely safe: if a URL is missing, it is skipped.
    """

    # You may configure ANY of these in Render / Vercel / local env:
    # KEEPALIVE_SUPABASE_URL
    # KEEPALIVE_RENDER_URL
    # KEEPALIVE_VERCEL_URL
    # KEEPALIVE_CUSTOM_1
    # KEEPALIVE_CUSTOM_2

    urls = [
        os.getenv("KEEPALIVE_SUPABASE_URL"),
        os.getenv("KEEPALIVE_RENDER_URL"),
        os.getenv("KEEPALIVE_VERCEL_URL"),
        os.getenv("KEEPALIVE_CUSTOM_1"),
        os.getenv("KEEPALIVE_CUSTOM_2"),
    ]

    # Remove empty values
    urls = [u for u in urls if u]

    if not urls:
        print("[keepalive] No keepalive URLs configured.")
        return

    print("[keepalive] Active URLs:")
    for u in urls:
        print("   →", u)

    async def ping_all():
        async with httpx.AsyncClient(timeout=10) as client:
            for url in urls:
                try:
                    await client.get(url)
                except Exception:
                    # Always silent — keepalive should never crash the app
                    pass

    scheduler.add_job(
        ping_all,
        "interval",
        seconds=interval_seconds,
        id="keepalive_multi",
        replace_existing=True,
    )

    print(f"[keepalive] Scheduler registered, interval = {interval_seconds} seconds.")
