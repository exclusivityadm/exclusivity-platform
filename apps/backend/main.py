from __future__ import annotations

import os
import sys
import importlib
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------------------------------
# Make routes/ the import root
# ------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent
ROUTES_ROOT = BACKEND_ROOT / "routes"

if str(ROUTES_ROOT) not in sys.path:
    sys.path.insert(0, str(ROUTES_ROOT))

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
    return {"ok": True}

@app.get("/health")
def base_health():
    return {"ok": True}

def _mount(module: str):
    try:
        mod = importlib.import_module(module)
        app.include_router(mod.router)
        log.info(f"[ROUTER] Mounted {module}")
    except Exception as e:
        log.info(f"[ROUTER] Skip {module} ({e})")

# ---- ROUTES ----
_mount("routes.voice")
_mount("routes.ai")
_mount("routes.loyalty")
_mount("routes.health")
_mount("routes.onboarding")
_mount("routes.shopify")
_mount("routes.settings")
_mount("routes.supabase")
_mount("routes.blockchain")
