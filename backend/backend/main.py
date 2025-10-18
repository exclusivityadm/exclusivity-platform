from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import env

from .routers import health, ai, shopify, tokens, analytics, tiers, settings, voice

app = FastAPI(title="Exclusivity Platform API", version=env("APP_VERSION","1.0.0"))

origins = (env("CORS_ORIGINS") or "http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="")
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(voice.router, prefix="/voice", tags=["voice"])
app.include_router(shopify.router, prefix="/shopify", tags=["shopify"])
app.include_router(tokens.router, prefix="/tokens", tags=["tokens"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(tiers.router, prefix="/tiers", tags=["tiers"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
