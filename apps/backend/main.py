from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os, importlib

app = FastAPI(title="Exclusivity API", version="1.0.0")

# ---------------- CORS ----------------
# Prefer explicit allow list via CORS_ALLOW_ORIGINS.
# If not provided, fall back to a safe regex for Vercel + localhost:3000.
origins_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
explicit_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
allow_origin_regex = None
if not explicit_origins:
    allow_origin_regex = r"^https://.*\.vercel\.app$|^http://localhost:3000$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=explicit_origins,          # use explicit list when provided
    allow_origin_regex=allow_origin_regex,   # or fallback regex
    allow_credentials=True,
    allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Single canonical health endpoint (avoid duplicate/slash-redirects)
@app.get("/health")
def health():
    return {"ok": True}

def enabled(name: str, default: str = "true") -> bool:
    return (os.getenv(name, default) or "").lower() == "true"

def include_router_if_exists(module_path: str, attr: str = "router",
                             prefix: str | None = None, tags: list[str] | None = None):
    try:
        module = importlib.import_module(module_path)
        router = getattr(module, attr)
        if prefix or tags:
            app.include_router(router, prefix=prefix or "", tags=tags or [])
        else:
            app.include_router(router)
        return True
    except Exception:
        return False

@app.get("/")
def root():
    return {"status":"running","routes":["/health","/ai","/loyalty","/shopify"]}

# Keep ONLY your other existing routers here (NOT health again).
# If you previously included a separate health router, remove it to avoid /health -> 307.
include_router_if_exists("apps.backend.routes.supabase", prefix="/supabase", tags=["supabase"])
include_router_if_exists("apps.backend.routes.blockchain", prefix="/blockchain", tags=["blockchain"])
include_router_if_exists("apps.backend.routes.voice",     prefix="/voice",     tags=["voice"])

# New Insane-Mode routers (mount if present)
if enabled("FEATURE_LOYALTY", "true"):
    added = include_router_if_exists("apps.backend.routes.loyalty", prefix="/loyalty", tags=["loyalty"])
    if not added:
        include_router_if_exists("app.routers.loyalty")

if enabled("FEATURE_SHOPIFY_EMBED", "true"):
    added = include_router_if_exists("apps.backend.routes.shopify", prefix="/shopify", tags=["shopify"])
    if not added:
        include_router_if_exists("app.routers.shopify")

if enabled("FEATURE_AI_BRAND_BRAIN", "true"):
    added = include_router_if_exists("apps.backend.routes.ai", prefix="/ai", tags=["ai"])
    if not added:
        include_router_if_exists("app.routers.ai")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.app.main:app", host="0.0.0.0", port=int(os.getenv("PORT","10000")), reload=True)
