from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import importlib
import logging

log = logging.getLogger("uvicorn")

app = FastAPI(title="Exclusivity API", version="1.0.0")

# --- CORS
allow_origins = []
if os.getenv("CORS_ALLOW_ORIGINS"):
    allow_origins = [
        o.strip()
        for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
        if o.strip()
    ]

allow_origin_regex = None if allow_origins else r"^https://.*\.vercel\.app$|^http://localhost:3000$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"ok": True, "service": "exclusivity-backend"}

@app.get("/health")
def health():
    return {"ok": True}

def _mount(module_path: str):
    try:
        mod = importlib.import_module(module_path)
        app.include_router(mod.router)
        log.info(f"[ROUTER] Mounted {module_path}")
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
            "/core/*",
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
include_router_if_exists("apps.backend.routes.core", prefix="/core", tags=["core"])

include_router_if_exists("apps.backend.routes.supabase", prefix="/supabase", tags=["supabase"])
include_router_if_exists("apps.backend.routes.blockchain", prefix="/blockchain", tags=["blockchain"])
include_router_if_exists("apps.backend.routes.voice", prefix="/voice", tags=["voice"])

if enabled("FEATURE_AI_BRAND_BRAIN", "true"):
    include_router_if_exists("apps.backend.routes.ai", prefix="/ai", tags=["ai"])

# ---- ROUTES (CANONICAL) ----
_mount("apps.backend.routes.voice")
_mount("apps.backend.routes.ai")
_mount("apps.backend.routes.loyalty")
_mount("apps.backend.routes.health")
_mount("apps.backend.routes.onboarding")
_mount("apps.backend.routes.shopify")
_mount("apps.backend.routes.settings")
_mount("apps.backend.routes.supabase")
_mount("apps.backend.routes.blockchain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        reload=True,
    )
