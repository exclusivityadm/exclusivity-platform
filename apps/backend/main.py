# apps/backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import os
import importlib
import logging

log = logging.getLogger("uvicorn")

# ----------------------------------------------------------
# APP
# ----------------------------------------------------------
app = FastAPI(title="Exclusivity API", version="1.0.0")

# ----------------------------------------------------------
# CORS
# ----------------------------------------------------------
origins_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
allow_origin_regex = None if allow_origins else r"^https://.*\.vercel\.app$|^http://localhost:3000$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ----------------------------------------------------------
# HEALTH CHECK
# ----------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

# ----------------------------------------------------------
# KEEPALIVE (APScheduler)
# ----------------------------------------------------------
scheduler = AsyncIOScheduler()

try:
    # definitive correct location
    import apps.backend.services.keepalive as keepalive_module
    _keepalive_available = True
    log.info("[KEEPALIVE] keepalive module loaded from services.keepalive")
except Exception as e:
    keepalive_module = None
    _keepalive_available = False
    log.error(f"[KEEPALIVE] Failed to load keepalive module: {e}")

def keepalive_job():
    """
    Runs periodically to ping Supabase, Render, and Vercel.
    """
    if not _keepalive_available:
        log.warning("[KEEPALIVE] keepalive module unavailable, skipping ping cycle.")
        return

    try:
        keepalive_module.keep_supabase_alive()
        keepalive_module.keep_render_alive()
        keepalive_module.keep_vercel_alive()
        log.info("[KEEPALIVE] Ping cycle completed.")
    except Exception as e:
        log.error(f"[KEEPALIVE] Error in ping cycle: {e}")

@app.on_event("startup")
def start_scheduler():
    """
    Start APScheduler on startup with a 5-minute interval.
    """
    if not _keepalive_available:
        log.warning("[KEEPALIVE] Scheduler not started — keepalive module missing.")
        return

    scheduler.add_job(
        keepalive_job,
        IntervalTrigger(minutes=5),
        id="keepalive_job",
        replace_existing=True
    )
    scheduler.start()
    log.info("[KEEPALIVE] APScheduler started (runs every 5 minutes).")

# ----------------------------------------------------------
# FEATURE FLAGS
# ----------------------------------------------------------
def enabled(name: str, default: str = "true") -> bool:
    return (os.getenv(name, default) or "").lower() == "true"

# ----------------------------------------------------------
# ROUTER LOADER
# ----------------------------------------------------------
def include_router_if_exists(
    module_path: str,
    attr: str = "router",
    prefix: str | None = None,
    tags: list[str] | None = None
):
    try:
        module = importlib.import_module(module_path)
        router = getattr(module, attr)
        app.include_router(router, prefix=prefix or "", tags=tags or [])
        log.info(f"[ROUTER] Mounted {module_path}")
        return True
    except Exception as e:
        log.info(f"[ROUTER] Skip {module_path} ({e})")
        return False

# ----------------------------------------------------------
# ROOT ENDPOINT
# ----------------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "running",
        "routes_hint": [
            "/health",
            "/debug/routes",
            "/voice/*",
            "/ai/*",
            "/merchant/*",
            "/loyalty/*",
            "/shopify/*",
        ],
    }

# ----------------------------------------------------------
# ROUTES
# ----------------------------------------------------------
include_router_if_exists("apps.backend.routes.supabase", prefix="/supabase", tags=["supabase"])
include_router_if_exists("apps.backend.routes.blockchain", prefix="/blockchain", tags=["blockchain"])
include_router_if_exists("apps.backend.routes.voice", prefix="/voice", tags=["voice"])

if enabled("FEATURE_AI_BRAND_BRAIN", "true"):
    include_router_if_exists("apps.backend.routes.ai", prefix="/ai", tags=["ai"])

if enabled("FEATURE_LOYALTY", "true"):
    include_router_if_exists("apps.backend.routes.loyalty", prefix="/loyalty", tags=["loyalty"])
    include_router_if_exists("apps.backend.routes.merchant", prefix="/merchant", tags=["merchant"])

if enabled("FEATURE_SHOPIFY_EMBED", "true"):
    include_router_if_exists("apps.backend.routes.shopify", prefix="/shopify", tags=["shopify"])

# ----------------------------------------------------------
# DEBUG ROUTES
# ----------------------------------------------------------
@app.get("/debug/routes")
def debug_routes():
    return [
        {"path": r.path, "name": r.name, "methods": list(r.methods or [])}
        for r in app.router.routes
    ]

# ----------------------------------------------------------
# MAIN ENTRY
# ----------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        reload=True
    )
