from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Exclusivity Backend", version="2.0.0")

# Allow frontend and local origins
origins = [
    "http://localhost:3000",
    "https://exclusivity-platform.vercel.app",
    "https://exclusivity-frontend.vercel.app",
    "https://exclusivity.vip",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# --- ROUTE IMPORTS ---
from apps.backend.routes import (
    health,
    supabase,
    blockchain,
    voice,
    ai,
    analytics,
    creative,
    loyalty,
    marketing,
    security,
    tax
)

# --- ROUTE REGISTRATION ---
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(supabase.router, prefix="/supabase", tags=["Supabase"])
app.include_router(blockchain.router, prefix="/blockchain", tags=["Blockchain"])
app.include_router(voice.router, prefix="/voice", tags=["Voice"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(creative.router, prefix="/creative", tags=["Creative"])
app.include_router(loyalty.router, prefix="/loyalty", tags=["Loyalty"])
app.include_router(marketing.router, prefix="/marketing", tags=["Marketing"])
app.include_router(security.router, prefix="/security", tags=["Security"])
app.include_router(tax.router, prefix="/tax", tags=["Tax"])

# --- ROOT ENDPOINT ---
@app.get("/")
def root():
    return {"status": "ok", "message": "Exclusivity Backend v2 is live"}

# --- UVICORN ENTRY POINT ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
