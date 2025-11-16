# apps/backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os, importlib, logging

log = logging.getLogger("uvicorn")
app = FastAPI(title="Exclusivity API", version="1.0.0")

# ----------------------------------------------------------
# CORS
# ----------------------------------------------------------
origins_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

# If allowlist empty → use regex for Vercel + local dev
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
# Health
# ----------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------
def enabled(name: str, default: str = "true") -> bool:
    """Feature flag helper: returns True if env var is 'true'."""
    return (os.getenv(name, default) or "").lower() == "true"


def include_router_if_exists(module_path: str, attr: str = "router",
                             prefix: str | None = None, tags: list[str] | None = None) -> bool:
    """
    Safely import and mount a router.
    Never breaks the app if router or module is missing.
    """
    try:
        mod = importlib.import_module(module_path)
        router = getattr(mod, attr)
        app.include_router(router, prefix=prefix or "", tags=tags or [])
        log.info(f"[ROUTER] Mounted {module_path} at '{prefix or ''}'")
        return True
    except Exception as e:
        log.info(f"[ROUTER] Skipped {module_path} ({e})")
        return False

# ----------------------------------------------------------
# Root
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
            "/merchant/points/*",
            "/loyalty/*",
            "/shopify/*",
        ]
    }

# ----------------------------------------------------------
# Always-on routers
# ----------------------------------------------------------
include_router_if_exists("apps.backend.routes.voice",          prefix="/voice",    tags=["voice"])
include_router_if_exists("apps.backend.routes.ai",             prefix="/ai",       tags=["ai"])
include_router_if_exists("apps.backend.routes.supabase_debug", prefix="",          tags=["debug"])

# ----------------------------------------------------------
# Loyalty system (merchant + points + loyalty engine)
# ----------------------------------------------------------
if enabled("FEATURE_LOYALTY", "true"):
    include_router_if_exists("apps.backend.routes.merchant",        prefix="/merchant",        tags=["merchant"])
    include_router_if_exists("apps.backend.routes.merchant_points", prefix="/merchant/points", tags=["merchant-points"])
    include_router_if_exists("apps.backend.routes.loyalty",         prefix="/loyalty",         tags=["loyalty"])

# ----------------------------------------------------------
# Shopify embedded app + OAuth + Webhooks
# ----------------------------------------------------------
if enabled("FEATURE_SHOPIFY_EMBED", "true"):
    include_router_if_exists(
        "apps.backend.routes.shopify",
        prefix="/shopify",
        tags=["shopify"]
    )
