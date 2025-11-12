# apps/backend/utils/keepalive.py
import os
import asyncio
from typing import Optional, Callable
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Environment
KEEPALIVE_ENABLED = os.getenv("KEEPALIVE_ENABLED", "true").lower() == "true"
SUPABASE_URL      = os.getenv("SUPABASE_URL", "").rstrip("/")
VERCEL_URL        = os.getenv("VERCEL_URL", "").rstrip("/")
RENDER_SELF_URL   = os.getenv("RENDER_SELF_URL", "").rstrip("/")  # optional: your Render URL if you want to ping external

# Single global scheduler instance (self-healing on restarts)
_scheduler: Optional[AsyncIOScheduler] = None

async def _safe_get(url: str, timeout: float = 8.0):
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            await client.get(url)
    except Exception:
        # intentionally quiet (no logs) per your preference
        pass

async def _ping_render():
    # Prefer internal route to avoid external egress; '/' is fine
    await _safe_get("http://127.0.0.1:10000/health/")

async def _ping_supabase():
    # Rest v1 base (no auth required path). If your project enforces auth, switch to /auth/v1/health or a public RPC.
    if SUPABASE_URL:
        await _safe_get(f"{SUPABASE_URL}/auth/v1/health")

async def _ping_vercel():
    if VERCEL_URL:
        await _safe_get(f"{VERCEL_URL}/")

def _add_job(func: Callable, seconds: int):
    global _scheduler
    if not _scheduler:
        return
    _scheduler.add_job(func, IntervalTrigger(seconds=seconds), max_instances=1, coalesce=True, misfire_grace_time=30)

async def setup_keepalive(app=None):
    """
    Create (or re-create) a resilient APScheduler that pings:
      - Render backend every 5 min
      - Supabase every 15 min
      - Vercel every 30 min
    """
    global _scheduler
    if not KEEPALIVE_ENABLED:
        return

    # If scheduler exists but isn't running, start it; else create a new one.
    try:
        if _scheduler is None:
            _scheduler = AsyncIOScheduler()
        if not _scheduler.running:
            _scheduler.start()
            # register jobs
            _add_job(_ping_render, 5 * 60)
            _add_job(_ping_supabase, 15 * 60)
            _add_job(_ping_vercel, 30 * 60)

            # self-healing: periodically verify scheduler is alive (every 10 minutes)
            async def _watchdog():
                while True:
                    if _scheduler is None or not _scheduler.running:
                        try:
                            await setup_keepalive(app)
                        except Exception:
                            pass
                    await asyncio.sleep(600)

            # spawn watchdog (fire-and-forget)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_watchdog())
            except RuntimeError:
                # no running loop (unlikely in FastAPI), do nothing
                pass
    except Exception:
        # stay quiet per your "no logs" preference
        pass
