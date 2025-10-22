# main.py — universal safe import handler
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Path repair ---
# Ensure Python can always find the current and parent backend dirs
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
sys.path.append(CURRENT_DIR)
if PARENT_DIR not in sys.path:
sys.path.append(PARENT_DIR)

# --- Import routers safely ---
try:
from routers import voice # Normal relative import
except ModuleNotFoundError:
import importlib
voice = importlib.import_module("backend.routers.voice")

# --- FastAPI initialization ---
app = FastAPI(title="Exclusivity Backend", version="1.0")

# --- CORS setup ---
app.add_middleware(
CORSMiddleware,
allow_origins=["*"], # You can restrict to your Vercel domain later
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)

# --- Include routers ---
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])

# --- Root route ---
@app.get("/")
async def root():
return {"status": "ok", "message": "Exclusivity backend operational."}

# --- Healthcheck endpoint ---
@app.get("/health")
async def health_check():
return {"status": "healthy", "environment": os.getenv("ENV", "development")}


# --- Run manually for local dev ---
if __name__ == "__main__":
import uvicorn
uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
