# apps/backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os, importlib, logging

log = logging.getLogger("uvicorn")
app = FastAPI(title="Exclusivity API", version="1.0.0")

# ---------- CORS ----------
# Option A: set an explicit allowlist via CORS_ALLOW_ORIGINS (comma-separated).
# Option B: leave it empty and we allow *.vercel.app + localhost:3000 via regex.
origins_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
allow_origin_regex = None if allow_origins else r"^https://.*\.vercel\.app$|^http://localhost:3000$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ---------- Health ----------
@app.get("/health")
def health():
    return {"ok": True}

# ---------- Helpers ----------
def enabled(name: str, default: str = "true") -> bool:
    """Feature flag helper: returns True iff env var is 'true' (case-insensitive)."""
    return (os.getenv(name, default) or "").lower() == "true"

def include_router_if_exists(module_path: str, attr: str = "router",
                             prefix: str | None = None, tags: list[str] | None = None) -> bool:
    """
    Try to import a module and include its APIRouter. Returns True if mounted.
    Never crashes the app if module is missing or import fails.
    """
    try:
        mod = importlib.import_module(module_path)
        router = getattr(mod, attr)
        app.include_router(router, prefix=prefix or "", tags=tags or [])
        log.info(f"[ROUTER] Mounted {module_path} at '{prefix or ''}'")
        return True
    except Exception as e:
        log.info(f"[ROUTER] Skip {module_path} ({e})")
        return False

@app.get("/")
def root():
    return {
        "status": "running",
        "routes_hint": [
            "/health", "/debug/routes",
            "/voice/*", "/ai/*",
            "/merchant/*", "/merchant/points/*",
            "/loyalty/*", "/shopify/*"
        ]
    }

# ---------- Always-on routers ----------
include_router_if_exists("apps.backend.routes.voice",          prefix="/voice",    tags=["voice"])
include_router_if_exists("apps.backend.routes.ai",             prefix="/ai",       tags=["ai"])
include_router_if_exists("apps.backend.routes.supabase_debug", prefix="",          tags=["debug"])

# ---------- Loyalty (points engine + merchant config) ----------
if enabled("FEATURE_LOYALTY", "true"):
    include_router_if_exists("apps.backend.routes.merchant",        prefix="/merchant",         tags=["merchant"])
    include_router_if_exists("apps.backend.routes.merchant_points", prefix="/merchant/points",  tags=["merchant-points"])
    include_router_if_exists("apps.backend.routes.loyalty",         prefix="/loyalty",          tags=["loyalty"])

# ---------- Shopify (embedded app + webhooks) ----------
if enabled("FEATURE_SHOPIFY_EMBED", "true"):
    include_router_if_exists("apps.backend.routes.shopify",         prefix="/shopify",_
