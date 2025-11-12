from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Route modules
from apps.backend.routes import health, supabase, blockchain, voice, orion, lyric
# Keepalive scheduler
from apps.backend.utils.keepalive import setup_keepalive

app = FastAPI(
    title="Exclusivity Backend API",
    description="Backend services for Exclusivity platform (voice, supabase, blockchain, etc.)",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten later to your Vercel domain if desired
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers (note the trailing-slash style)
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(supabase.router, prefix="/supabase", tags=["supabase"])
app.include_router(blockchain.router, prefix="/blockchain", tags=["blockchain"])
app.include_router(voice.router, prefix="/voice", tags=["voice"])
app.include_router(orion.router, prefix="/orion", tags=["voice"])
app.include_router(lyric.router, prefix="/lyric", tags=["voice"])

@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "Exclusivity Backend",
        "routes": ["/health", "/supabase", "/blockchain", "/voice", "/orion", "/lyric"],
    }

# Start keepalives as soon as the app is up
@app.on_event("startup")
async def _start_keepalive():
    await setup_keepalive(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.main:app", host="0.0.0.0", port=10000, reload=True)
