from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import route modules
from apps.backend.routes import health, supabase, blockchain, voice

# Initialize FastAPI app
app = FastAPI(
    title="Exclusivity Backend API",
    description="Backend services for Exclusivity platform (voice, supabase, blockchain, etc.)",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # can be limited later to your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health & Core Routes
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(supabase.router, prefix="/supabase", tags=["supabase"])
app.include_router(blockchain.router, prefix="/blockchain", tags=["blockchain"])

# Voice routes (single router file)
app.include_router(voice.router, prefix="/voice", tags=["voice"])

@app.get("/")
async def root():
    """Root endpoint for uptime verification."""
    return {
        "status": "running",
        "service": "Exclusivity Backend",
        "routes": [
            "/health",
            "/supabase",
            "/blockchain",
            "/voice",
        ],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.main:app", host="0.0.0.0", port=10000, reload=True)
