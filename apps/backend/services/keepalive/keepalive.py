import os
import logging
import httpx
from supabase import create_client, Client

log = logging.getLogger("uvicorn")

# ----------------------------------------------------------
# ENVIRONMENT
# ----------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

RENDER_URL = os.getenv("KEEPALIVE_RENDER_URL", "").strip()
VERCEL_URL = os.getenv("KEEPALIVE_VERCEL_URL", "").strip()

# ----------------------------------------------------------
# SUPABASE CLIENT (SERVICE ROLE)
# ----------------------------------------------------------
_supabase_client: Client | None = None

def get_supabase() -> Client | None:
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        log.warning("[KEEPALIVE] Supabase env vars missing — cannot initialize client.")
        return None

    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        log.info("[KEEPALIVE] Supabase client initialized.")
        return _supabase_client
    except Exception as e:
        log.error(f"[KEEPALIVE] Failed to initialize Supabase client: {e}")
        return None


# ----------------------------------------------------------
# PING: SUPABASE (REAL DB ACTIVITY)
# ----------------------------------------------------------
def keep_supabase_alive():
    """
    Performs a real DB SELECT to guarantee Supabase registers activity.
    """
    client = get_supabase()
    if client is None:
        log.warning("[KEEPALIVE] Cannot ping Supabase — client not available.")
        return

    try:
        # Use the lightest valid activity: a select on ANY public table
        # Change 'profiles' to any table that always exists in your schema.
        response = client.table("profiles").select("id").limit(1).execute()
        log.info("[KEEPALIVE] Supabase ping OK.")
    except Exception as e:
        log.error(f"[KEEPALIVE] Supabase ping FAILED: {e}")


# ----------------------------------------------------------
# PING: RENDER HEALTH
# ----------------------------------------------------------
def keep_render_alive():
    """
    Sends a GET request to Render to keep the backend container warm.
    """
    if not RENDER_URL:
        log.debug("[KEEPALIVE] No Render URL configured.")
        return

    try:
        httpx.get(RENDER_URL, timeout=10)
        log.info("[KEEPALIVE] Render ping OK.")
    except Exception as e:
        log.error(f"[KEEPALIVE] Render ping FAILED: {e}")


# ----------------------------------------------------------
# PING: VERCEL DEPLOYMENT
# ----------------------------------------------------------
def keep_vercel_alive():
    """
    Sends a GET request to Vercel frontend (if configured).
    """
    if not VERCEL_URL:
        log.debug("[KEEPALIVE] No Vercel URL configured.")
        return

    try:
        httpx.get(VERCEL_URL, timeout=10)
        log.info("[KEEPALIVE] Vercel ping OK.")
    except Exception as e:
        log.error(f"[KEEPALIVE] Vercel ping FAILED: {e}")
