from fastapi import APIRouter, Request
from supabase import create_client, Client
import os

from apps.backend.utils.ether_edge import enforce_ether_headers, EtherEdgeError
from apps.backend.utils.envelope import ok, error

router = APIRouter(prefix="/supabase", tags=["Supabase"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


@router.get("/check")
async def supabase_check(request: Request):
    """
    Check connection to Supabase and confirm tables exist.
    Full overwrite version — no partial edits.
    """
    try:
        # Ether enforcement is OPTIONAL and explicit.
        # Uncomment ONLY if/when this route must be internal-only.
        # enforce_ether_headers(request)

        if not SUPABASE_URL or not SUPABASE_KEY:
            return error("Missing Supabase credentials", "supabase_config", 500)

        client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = client.table("profiles").select("*").limit(1).execute()
        count = len(result.data) if result.data else 0

        return ok(
            data={
                "connected": True,
                "rows_found": count,
                "message": "Supabase reachable.",
            }
        )

    except EtherEdgeError as e:
        return error(e.message, "ether_edge", e.status_code)
    except Exception as e:
        return error(str(e), "supabase_error", 500)
