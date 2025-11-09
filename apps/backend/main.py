import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# === Patch for Supabase Realtime Import Bug (Render Safe) ===
# Ensures websockets.asyncio exists for libraries expecting it
try:
    import types, websockets
    if not hasattr(websockets, "asyncio"):
        websockets.asyncio = types.ModuleType("websockets.asyncio")
        from websockets.legacy import client as legacy_client
        websockets.asyncio.client = legacy_client
        sys.modules["websockets.asyncio"] = websockets.asyncio
        sys.modules["websockets.asyncio.client"] = legacy_client
except Exception as e:
    print(f"[WARN] Websockets patch failed: {e}")
# ============================================================

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Exclusivity Backend", version="2.0")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production domains later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTE IMPORTS ---
try:
    from apps.backend.routes import (
        ai,
        loyalty,
        analytics,
        creative,
        marketing,
        tax,
        security,
    )

    app.include_router(ai.router, prefix="/ai", tags=["AI"])
    app.include_router(loyalty.router, prefix="/loyalty", tags=["Loyalty"])
    app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
    app.include_router(creative.router, prefix="/creative", tags=["Creative"])
    app.include_router(marketing.router, prefix="/marketing", tags=["Marketing"])
    app.include_router(tax.router, prefix="/tax", tags=["Tax"])
    app.include_router(security.router, prefix="/security", tags=["Security"])

except ModuleNotFoundError as e:
    print(f"[WARN] Optional route not found: {e}")
except Exception as e:
    print(f"[ERROR] Route import failed: {e}")

# --- SYSTEM HEALTH ENDPOINTS ---
@app.get("/health")
def health():
    """Basic Render & local health check."""
    return {"status": "ok", "service": "backend"}


@app.get("/env")
def check_env():
    """Verify core environment variables are loading."""
    keys = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "ELEVENLABS_API_KEY",
        "OPENAI_API_KEY",
        "BASE_CHAIN_ID",
    ]
    env_report = {k: bool(os.getenv(k)) for k in keys}
    return {"env_loaded": all(env_report.values()), "details": env_report}


# --- CHAIN STATUS ENDPOINT ---
@app.get("/chain")
def check_chain():
    """Simulated blockchain connection check (Base Mainnet)."""
    chain_id_hex = "0x2105"
    chain_id_decimal = int(chain_id_hex, 16)
    return {
        "connected": True,
        "chain_id_hex": chain_id_hex,
        "chain_id_decimal": chain_id_decimal,
        "minting_enabled": "true",
        "aesthetics_enabled": "true",
        "wallets": {"brand_wallet": "", "developer_wallet": ""},
        "coinbase_network": "base-mainnet",
        "domain_allowlist": "exclusivity.vip",
    }


# --- SUPABASE TEST ENDPOINT ---
@app.get("/supabase")
def check_supabase():
    """Verify Supabase credentials and schema."""
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return {"connected": False, "error": "Missing Supabase credentials in environment."}

    try:
        supabase = create_client(url, key)
        data = supabase.table("profiles").select("*").limit(1).execute()
        return {"connected": True, "response": data}
    except Exception as e:
        return {"connected": False, "error": str(e)}


# --- ORION & LYRIC TEST ENDPOINTS ---
@app.get("/voice/orion")
def voice_orion():
    """Generate Orion sample audio (Base64 output)."""
    from openai import OpenAI
    import base64

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input="Orion online and fully operational.",
        )
        audio_bytes = speech.read()
        return {
            "speaker": "orion",
            "length_bytes": len(audio_bytes),
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
        }
    except Exception as e:
        return {"error": f"TTS request failed: {e}"}


@app.get("/voice/lyric")
def voice_lyric():
    """Generate Lyric sample audio (Base64 output)."""
    from openai import OpenAI
    import base64

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        speech = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="verse",
            input="Lyric standing by and synchronized.",
        )
        audio_bytes = speech.read()
        return {
            "speaker": "lyric",
            "length_bytes": len(audio_bytes),
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
        }
    except Exception as e:
        return {"error": f"TTS request failed: {e}"}


# --- ROOT ---
@app.get("/")
def root():
    """Default route."""
    return {"message": "Exclusivity Backend API active", "version": "2.0"}


# --- ENTRYPOINT ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.backend.main:app", host="0.0.0.0", port=10000, reload=True)
