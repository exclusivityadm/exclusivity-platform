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
    allow_origins=["*"],  # Can be restricted later to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check route
app.include_router(health.router, prefix="/health", tags=["health"])

# Core routes
app.include_router(supabase.router, prefix="/supabase", tags=["supabase"])
app.include_router(blockchain.router, prefix="/blockchain", tags=["blockchain"])
app.include_router(voice.router, prefix="/voice", tags=["voice"])

# Root route for quick verification
@app.get("/")
async def root():
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

# Entry point for Render and local dev
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.main:app", host="0.0.0.0", port=10000, reload=True)
