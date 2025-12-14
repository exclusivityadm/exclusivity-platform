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
    expose_headers=["*"],
)

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
_mount("apps.backend.routes.settings")   # Drop D
_mount("apps.backend.routes.supabase")
_mount("apps.backend.routes.blockchain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        reload=True
    )
