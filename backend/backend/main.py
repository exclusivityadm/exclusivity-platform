from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .modules.conversational_ai.router import router as ai_router

app = FastAPI(title="Exclusivity Backend", version="2025.01")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "env": settings.ENVIRONMENT}

app.include_router(ai_router, prefix="/ai", tags=["ai"])

def get_supabase_client():
    try:
        from supabase import create_client, Client  # type: ignore
    except Exception as e:
        raise RuntimeError("Supabase client import failed. Error: %s" % e)
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise RuntimeError("Supabase credentials are missing.")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
