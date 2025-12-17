from __future__ import annotations

import asyncio
import httpx
import os


async def run_keepalive() -> None:
    """
    Non-destructive keepalive pings.
    Safe to call repeatedly.
    """

    urls = []

    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url:
        urls.append(supabase_url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in urls:
            try:
                await client.get(url)
            except Exception:
                pass

    await asyncio.sleep(0)
