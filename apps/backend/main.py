# apps/backend/main.py
"""
Main entrypoint for Exclusivity Backend (Phase 2 Stable Build)
Now includes runtime patch to suppress the 'ClientConnection' import error
caused by Supabase Realtime + websockets >=12.0.
"""

import sys
import types
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# -------------------------------------------------------------------
# STEP 1 — Runtime patch for Supabase websocket import error
# -------------------------------------------------------------------
try:
    import websockets
    # Create a shim so anything trying to import websockets.legacy.client works
    if not hasattr(websockets, "legacy"):
        legacy = types.SimpleNamespace()
        client = types.SimpleNamespace(ClientConnection=getattr(websockets.client, "ClientConnection", object))
        legacy.client = client
        websockets.legacy = legacy
        sys.modules["websockets.legacy"] = legacy
        sys.modules["websockets.legacy.client"] = client
except Exception as e:
    logging.warning(f"WebSocket shim patch skipped: {e}")

# -------------------------------------------------------------------
# STEP 2 — Load environment variables
# -------------------------------------------------------------------
load_dotenv()

# -------------------------------------------------------------------
# STEP 3 — Initialize FastAPI app
# -------------------------------------------------------------------
app = FastAPI(title="Exclusivity Backend", version="2.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # can restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# STEP 4 — Import routes AFTER patch + app init
# -------------------------------------------------------------------
from apps.backend.routes import health, supabase, blockchain, voice

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(supabase.router, prefix="/supabase", tags=["Supabase"])
app.include_router(blockchain.router, prefix="/blockchain", tags=["Blockchain"])
app.include_router(voice.router, prefix="/voice", tags=["Voice"])

# -------------------------------------------------------------------
# STEP 5 — Root endpoint
# -------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "online", "environment": os.getenv("ENVIRONMENT", "production")}

# -------------------------------------------------------------------
# STEP 6 — Local dev runner
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.main:app", host="0.0.0.0", port=10000, reload=True)
