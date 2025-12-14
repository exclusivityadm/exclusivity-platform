from __future__ import annotations

import os
import sys
import importlib
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------------------------------
# CRITICAL: Ensure backend root is on sys.path
# ------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent.parent  # repo root

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ------------------------------------------------------------
# App setup
# ------------------------------------------------------------
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
    expose_headers=["*"],
)

# ------------------------------------------------------------
# Core routes
# ------------------------------------------------------------
@app.get("/")
def root():
    return {"ok": True, "service": "exclusivity-backend"}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/debug/routes")
def debug_routes():
    return [
        {"path": getattr(r, "path", None), "name": getattr(r, "name", None)}
        for r in app.router.routes
    ]


# ------------------------------------------------------------
# Router loader
# ------------------------------------------------------------
def _mount(module_path: str):
    try:
        mod = importlib.import_module(module_path)
        app.include_router(mod.router)
        log.info(f"[ROUTER] Mounted {module_path}")
    except Exception as e:
        log.info(f"[ROUTER] Skip {module_path} ({e})")


# ---- ROUTES (ORDERED, EXPLICIT) ----
_mount("apps.backend.routes.voice")
_mount("apps.backend.routes.ai")
_mount("apps.backend.routes.loyalty")
_mount("apps.backend.routes.onboarding")
_mount("apps.backend.routes.shopify")
_mount("apps.backend.routes.settings")
_mount("apps.backend.routes.supabase")
_mount("apps.backend.routes.blockchain")
_mount("apps.backend.routes.health")

# ------------------------------------------------------------
# Local dev entry
# ------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "apps.backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        reload=True,
    )
