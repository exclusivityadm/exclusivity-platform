import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Route imports
from apps.backend.routes import health, supabase, blockchain, voice

# Initialize FastAPI app
app = FastAPI(
    title="Exclusivity Backend",
    version="1.0.0",
    description="Core backend API for Exclusivity merchant console.",
)

# --- CORS CONFIG ---
frontend_url = os.getenv("FRONTEND_URL", "https://exclusivity-platform.vercel.app")
origins = [
    frontend_url,
    "http://localhost:3000",
    "https://exclusivity-platform.vercel.app",
    "https://exclusivity.vip",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---
app.include_router(health.router)
app.include_router(supabase.router)
app.include_router(blockchain.router)
app.include_router(voice.router)


# --- ROOT ROUTE ---
@app.get("/")
async def root():
    """Base landing endpoint."""
    return JSONResponse(
        content={
            "app": "Exclusivity Backend",
            "status": "online",
            "routes": ["/health", "/supabase/check", "/blockchain/status", "/voice/orion", "/voice/lyric"],
        }
    )


# --- ERROR HANDLER ---
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "path": str(request.url)},
    )
