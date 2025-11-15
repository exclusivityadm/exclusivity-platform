from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os, importlib, logging

log = logging.getLogger("uvicorn")
app = FastAPI(title="Exclusivity API", version="1.0.0")

# ----- CORS -----
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

@app.get("/health")
def health(): return {"ok": True}

def enabled(name: str, default: str = "true") -> bool:
    return (os.getenv(name, default) or "").lower() == "true"

def include_router_if_exists(module_path: str, attr: str = "router",
                             prefix: str | None = None, tags: list[str] | None = None) -> bool:
    try:
        m = importlib.import_module(module_path)
        r = getattr(m, attr)
        app.include_router(r, prefix=prefix or "", tags=tags or [])
        log.info(f"[ROUTER] Mounted {module_path} at '{prefix or ''}'")
        return True
    except Exception as e:
        log.info(f"[ROUTER] Skip {module_path} ({e})")
        return False

@app.get("/")
def root():
    return {"status":"running","routes_hint":["/health","/voice/*","/ai/*","/merchant/*","/loyalty/*","/debug/supabase"]}

# Always-on
include_router_if_exists("apps.backend.routes.voice",           prefix="/voice",    tags=["voice"])
include_router_if_exists("apps.backend.routes.ai",              prefix="/ai",       tags=["ai"])
include_router_if_exists("apps.backend.routes.supabase_debug",  prefix="",          tags=["debug"])

# Feature-flagged
if enabled("FEATURE_LOYALTY", "true"):
    include_router_if_exists("apps.backend.routes.merchant",    prefix="/merchant", tags=["merchant"])
    include_router_if_exists("apps.backend.routes.loyalty",     prefix="/loyalty",  tags=["loyalty"])

# Optional future:
if enabled("FEATURE_SHOPIFY_EMBED", "false"):
    include_router_if_exists("apps.backend.routes.shopify",     prefix="/shopify",  tags=["shopify"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT","10000")), reload=True)
