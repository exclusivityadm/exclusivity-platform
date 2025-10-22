import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Handle path imports ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)

from routers import voice  # <- ensure you have backend/routers/voice.py

app = FastAPI(title="Exclusivity Backend")

# --- CORS setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Root health check ---
@app.get("/")
def root():
    return {"status": "ok", "message": "Backend is running successfully."}

# --- Include routes ---
app.include_router(voice.router, prefix="/voice", tags=["Voice"])

# --- Local dev entry point ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
