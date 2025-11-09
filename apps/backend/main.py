# apps/backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.backend.routes import health, supabase, blockchain, voice

app = FastAPI(
    title="Exclusivity Backend",
    description="Unified backend for Exclusivity platform",
    version="1.0.0",
)

# --- CORS configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Route includes ---
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(supabase.router, prefix="/supabase", tags=["Supabase"])
app.include_router(blockchain.router, prefix="/blockchain", tags=["Blockchain"])
app.include_router(voice.router, prefix="/voice", tags=["Voice"])

# --- Root endpoint ---
@app.get("/")
async def root():
    return {"status": "online", "message": "Exclusivity backend is active and stable"}
