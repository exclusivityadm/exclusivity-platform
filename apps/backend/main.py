# apps/backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os, importlib, logging

# Keepalive system
from apps.backend.utils.keepalive import setup_keepalive

log = logging.getLogger("uvicorn")
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
# Health
# ----------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}


# ----------------------------------------------------------
# Feature flag helper
# ----------------------------------------------------------
def enabled(name: str, default: str = "true") -> bool:
    return (os.getenv(name, default) or "").lower() == "true"


# ----------------------------------------------------------
# Safe dynamic router mounting
# ----------------------------------------------------------
def include_router_if_exists(module_path: str, attr: str = "router",
                             prefix: str | None = None, tags: list[str] | None = None) -> bool:
    try:
        mod = importlib.import_module(module_path)
        router = getattr(mod, attr)
        app.include_router(router, prefix=prefix or "", tags=tags or [])
        log.info(f"[ROUTER] Mounted {module_path} at '{prefix or ''}'")
        return True
    except Exception:
        # silent on purpose (user prefers no logs)
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
# Loyalty + Points + Merchant Engine
# ----------------------------------------------------------
if enabled("FEATURE_LOYALTY", "true"):
    include_router_if_exists("apps.backend.routes.merchant",        prefix="/merchant",        tags=["merchant"])
    include_router_if_exists("apps.backend.routes.merchant_points", prefix="/merchant/points", tags=["merchant-points"])
    include_router_if_exists("apps.backend.routes.loyalty",         prefix="/loyalty",         tags=["loyalty"])


# ----------------------------------------------------------
# Shopify embedded app + OAuth + Webhooks
# ----------------------------------------------------------
if enabled("FEATURE_SHOPIFY_EMBED", "true"):
    include_router_if_exists("apps.backend.routes.shopify", prefix="/shopify", tags=["shopify"])


# ----------------------------------------------------------
# KEEPALIVE SYSTEM — RUNS IMMEDIATELY ON STARTUP
# ----------------------------------------------------------
@app.on_event("startup")
async def _startup_keepalive():
    await setup_keepalive(app)  # silent auto-run scheduler


# ----------------------------------------------------------
# Local Dev Entrypoint
# ----------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.main:app", host="0.0.0.0", port=10000, reload=True)
