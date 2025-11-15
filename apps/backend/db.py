import os
from typing import Optional
try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = None  # type: ignore

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def get_supabase() -> Optional["Client"]:
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and create_client):
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)  # type: ignore
    except Exception:
        return None
