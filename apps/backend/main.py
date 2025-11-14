# Merged main.py — preserves existing routes and adds new ones conditionally.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import importlib

# -----------------------------------------------------------------------------
# App metadata
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Exclusivity Backend API",
    description="Backend services for Exclusivity platform (voice, supabase, blockchain, etc.)",
    version="1.0.0",
)

# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------
origins_env = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = [o.strip() for o in origins_env.split(",")] if origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Helper: feature flags + safe include
# -----------------------------------------------------------------------------
def enabled(name: str, default: str = "true") -> bool:
    # default "true" so new routers are ON unless you flip them off via env
    return (os.getenv(name, default) or "").lower() == "true"

def include_router_if_exists(module_path: str, attr: str = "router", *, prefix: str | None = None, tags: list[str] | None = None):
    """Try to import a module and include its APIRouter without crashing if missing."""
    try:
        module = importlib.import_module(module_path)
        router = getattr(module, attr)
        # If caller passed prefix/tags, set them on the include; otherwise rely on router's own config
        if prefix or tags:
            app.include_router(router, prefix=prefix or "", tags=tags or [])
        else:
            app.include_router(router)
        return True
    except Exception:
        return False

# -----------------------------------------------------------------------------
# Root endpoint
# -----------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "Exclusivity Backend",
        "routes": [
            "/health",
            "/supabase",
            "/blockchain",
            "/voice",
            # new routes (conditionally added below):
            "/loyalty",
            "/shopify",
            "/ai",
        ],
    }

# -----------------------------------------------------------------------------
# Existing routes (PRESERVED from your current file)
# Path style: apps.backend.routes.<module>
# -----------------------------------------------------------------------------
include_router_if_exists("apps.backend.routes.health",   prefix="/health",     tags=["health"])
include_router_if_exists("apps.backend.routes.supabase", prefix="/supabase",   tags=["supabase"])
include_router_if_exists("apps.backend.routes.blockchain", prefix="/blockchain", tags=["blockchain"])
include_router_if_exists("apps.backend.routes.voice",    prefix="/voice",      tags=["voice"])

# -----------------------------------------------------------------------------
# New Insane-Mode routers (added if present)
# We try two locations to be flexible with your structure:
#   1) apps.backend.routes.<name>
#   2) app.routers.<name>           (if you use the "app/routers" layout)
# -----------------------------------------------------------------------------
# Loyalty
if enabled("FEATURE_LOYALTY", "true"):
    added = include_router_if_exists("apps.backend.routes.loyalty", prefix="/loyalty", tags=["loyalty"])
    if not added:
        include_router_if_exists("app.routers.loyalty")  # uses router's own prefix/tags if defined

# Shopify
if enabled("FEATURE_SHOPIFY_EMBED", "true"):
    added = include_router_if_exists("apps.backend.routes.shopify", prefix="/shopify", tags=["shopify"])
    if not added:
        include_router_if_exists("app.routers.shopify")

# AI Brand Brain
if enabled("FEATURE_AI_BRAND_BRAIN", "true"):
    added = include_router_if_exists("apps.backend.routes.ai", prefix="/ai", tags=["ai"])
    if not added:
        include_router_if_exists("app.routers.ai")

# -----------------------------------------------------------------------------
# __main__ runner (optional; safe to leave)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")), reload=True)
