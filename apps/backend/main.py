# apps/backend/main.py

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import os
import importlib
import logging
import time

from apps.backend.services.admin.logger import log_request_response

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
# ADMIN LOGGING MIDDLEWARE
# ----------------------------------------------------------
@app.middleware("http")
async def admin_logger_middleware(request: Request, call_next):
    start = time.time()
    response: Response = await call_next(request)
    await log_request_response(request, response, start)
    return response

# ----------------------------------------------------------
# HEALTH
# ----------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

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
    tags: list[str] | None = None,
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
# ROOT
# ----------------------------------------------------------
@app.get("/")
def root():
    return {"status": "running"}

# ----------------------------------------------------------
# ROUTES — CANONICAL ORDER
# ----------------------------------------------------------

# Admin + Monetization
include_router_if_exists("apps.backend.routes.admin", prefix="/admin", tags=["admin"])
include_router_if_exists("apps.backend.routes.monetize", prefix="", tags=["monetize"])

# Core services
include_router_if_exists("apps.backend.routes.supabase", prefix="/supabase", tags=["supabase"])
include_router_if_exists("apps.backend.routes.blockchain", prefix="/blockchain", tags=["blockchain"])
include_router_if_exists("apps.backend.routes.voice", prefix="/voice", tags=["voice"])

# Brand + Pricing Intelligence (NEW — install-time automation)
include_router_if_exists("apps.backend.routes.brand", prefix="/brand", tags=["brand"])
include_router_if_exists("apps.backend.routes.pricing", prefix="/pricing", tags=["pricing"])

# AI
if enabled("FEATURE_AI_BRAND_BRAIN", "true"):
    include_router_if_exists("apps.backend.routes.ai", prefix="/ai", tags=["ai"])

# Loyalty + Merchant
if enabled("FEATURE_LOYALTY", "true"):
    include_router_if_exists("apps.backend.routes.loyalty", prefix="/loyalty", tags=["loyalty"])
    include_router_if_exists("apps.backend.routes.merchant", prefix="/merchant", tags=["merchant"])

# Shopify
if enabled("FEATURE_SHOPIFY_EMBED", "true"):
    include_router_if_exists("apps.backend.routes.shopify", prefix="/shopify", tags=["shopify"])

# ----------------------------------------------------------
# DEBUG
# ----------------------------------------------------------
@app.get("/debug/routes")
def debug_routes():
    return [
        {"path": r.path, "name": r.name, "methods": list(r.methods or [])}
        for r in app.router.routes
    ]

# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        reload=True,
    )
