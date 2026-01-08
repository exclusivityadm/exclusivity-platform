# apps/backend/main.py
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import os, importlib, logging, time
from apps.backend.services.admin.logger import log_request_response

log = logging.getLogger("uvicorn")

app = FastAPI(title="Exclusivity API", version="1.0.0")

# ---------------- CORS ----------------
origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=None if origins else r"^https://.*\.vercel\.app$|^http://localhost:3000$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- LOGGING ----------------
@app.middleware("http")
async def audit_logger(request: Request, call_next):
    start = time.time()
    response: Response = await call_next(request)
    await log_request_response(request, response, start)
    return response

@app.get("/health")
def health():
    return {"ok": True}

def enabled(name: str, default="true") -> bool:
    return (os.getenv(name, default)).lower() == "true"

def include(module, prefix="", tags=None):
    try:
        m = importlib.import_module(module)
        app.include_router(m.router, prefix=prefix, tags=tags or [])
        log.info(f"[ROUTER] {module}")
    except Exception as e:
        log.info(f"[ROUTER] skip {module}: {e}")

# ---------------- ROUTES ----------------
include("apps.backend.routes.admin", "/admin", ["admin"])
include("apps.backend.routes.monetize", "", ["monetize"])
include("apps.backend.routes.supabase", "/supabase", ["supabase"])
include("apps.backend.routes.blockchain", "/blockchain", ["blockchain"])
include("apps.backend.routes.voice", "/voice", ["voice"])
include("apps.backend.routes.brand", "/brand", ["brand"])
include("apps.backend.routes.pricing", "/pricing", ["pricing"])

if enabled("FEATURE_AI"):
    include("apps.backend.routes.ai", "/ai", ["ai"])

if enabled("FEATURE_LOYALTY"):
    include("apps.backend.routes.loyalty", "/loyalty", ["loyalty"])
    include("apps.backend.routes.merchant", "/merchant", ["merchant"])

if enabled("FEATURE_SHOPIFY"):
    include("apps.backend.routes.shopify", "/shopify", ["shopify"])
    include("apps.backend.routes.shopify_oauth", "/shopify", ["shopify"])
    include("apps.backend.routes.shopify_backfill_worker", "", ["shopify-worker"])

@app.get("/debug/routes")
def debug_routes():
    return [{"path": r.path, "methods": list(r.methods or [])} for r in app.router.routes]
