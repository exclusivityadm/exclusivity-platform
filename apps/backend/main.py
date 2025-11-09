# =====================================================
# 🚀 Exclusivity Backend - Main Entry Point
# =====================================================

import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# -----------------------------------------------------
# 🌐 Environment Loader
# -----------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
ENV_PATH = os.path.join(ROOT_DIR, ".env")

# Load the .env file automatically at startup
if os.path.exists(ENV_PATH):
    load_dotenv(dotenv_path=ENV_PATH)
else:
    print("⚠️  Warning: .env file not found at", ENV_PATH)

# Add root directory to sys.path for reliable imports
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# -----------------------------------------------------
# 🧩 Imports
# -----------------------------------------------------
from apps.backend.routes import ai as ai_routes
from apps.backend.routes import creative, marketing, loyalty, analytics, tax, security
from apps.backend.services.keepalive.keepalive import schedule_keepalive

# -----------------------------------------------------
# ⚙️ App Configuration
# -----------------------------------------------------
app = FastAPI(title="Exclusivity Backend", version="1.5.0")

# -----------------------------------------------------
# 🌍 Middleware
# -----------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------
# 💓 Health Check
# -----------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "backend"}

# -----------------------------------------------------
# 🧭 Routers
# -----------------------------------------------------
app.include_router(ai_routes.router, prefix="/api/ai", tags=["ai"])
app.include_router(creative.router, prefix="/api/creative", tags=["creative"])
app.include_router(marketing.router, prefix="/api/marketing", tags=["marketing"])
app.include_router(loyalty.router, prefix="/api/loyalty", tags=["loyalty"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(tax.router, prefix="/api/tax", tags=["tax"])
app.include_router(security.router, prefix="/api/security", tags=["security"])

# -----------------------------------------------------
# ⏱ Scheduler
# -----------------------------------------------------
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def on_startup():
    if os.getenv("KEEPALIVE_ENABLED", "true").lower() == "true":
        interval = int(os.getenv("KEEPALIVE_INTERVAL", "300"))
        schedule_keepalive(scheduler, interval)
    scheduler.start()

# -----------------------------------------------------
# 🏁 Entry Point (local dev)
# -----------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.backend.main:app", host="0.0.0.0", port=8000, reload=True)
