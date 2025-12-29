# app/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.errors import install_error_handlers
from app.middleware.internal_gate import InternalOnlyGate

from app.routers.health import router as health_router
from app.routers.version import router as version_router
from app.routers.onboarding import router as onboarding_router
from app.routers.shopify import router as shopify_router
from app.routers.loyalty import router as loyalty_router
from app.routers.settings import router as settings_router
from app.routers.ai import router as ai_router

from app.utils.settings import settings

log = logging.getLogger("exclusivity.main")

app = FastAPI(
    title="Exclusivity Platform",
    version=settings.EXCLUSIVITY_VERSION,
    description="Merchant loyalty, identity, and rewards platform",
)

# -------------------------------------------------------------------
# Error handling (stable envelopes, no stack leaks)
# -------------------------------------------------------------------
install_error_handlers(app)

# -------------------------------------------------------------------
# CORS (merchant-facing, controlled)
# -------------------------------------------------------------------
if settings.CORS_MODE == "allowlist":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )

# -------------------------------------------------------------------
# Internal / Partner access gate
# (Shopify + admin + internal tools)
# -------------------------------------------------------------------
app.add_middleware(
    InternalOnlyGate,
    internal_token=settings.INTERNAL_TOKEN,
    allowed_sources=settings.ALLOWED_SOURCES,
    exempt_prefixes=(
        "/health",
        "/version",
        "/shopify",
        "/onboarding",
    ),
)

# -------------------------------------------------------------------
# Routers
# -------------------------------------------------------------------
app.include_router(health_router)
app.include_router(version_router)

app.include_router(onboarding_router)
app.include_router(shopify_router)

app.include_router(loyalty_router)
app.include_router(settings_router)
app.include_router(ai_router)

# -------------------------------------------------------------------
# Root
# -------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "status": "Exclusivity Online",
        "mode": "production",
        "product": "merchant-loyalty",
        "routes": [
            "/health",
            "/version",
            "/onboarding",
            "/shopify",
            "/loyalty",
            "/settings",
            "/ai",
        ],
    }

# -------------------------------------------------------------------
# Startup (no background jobs, no keepalive)
# -------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    log.info("Exclusivity starting — clean runtime, no background schedulers")
