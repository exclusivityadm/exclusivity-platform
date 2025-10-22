from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .modules.conversational_ai.router import router as ai_router
from routes import voice
     app.include_router(voice.router)
from routers import voice_router

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

# backend/backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# CORS (keep your existing origins; here’s a permissive example)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# NEW: register voice router
from .routes.voice import router as voice_router
app.include_router(voice_router)

