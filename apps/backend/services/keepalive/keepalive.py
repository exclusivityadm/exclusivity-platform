import os
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

def schedule_keepalive(scheduler: AsyncIOScheduler, interval_seconds: int = 300):
    target = os.getenv("KEEPALIVE_URL")
    if not target:
        return
    async def ping():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.get(target)
        except Exception:
            pass
    scheduler.add_job(ping, "interval", seconds=interval_seconds, id="keepalive", replace_existing=True)
