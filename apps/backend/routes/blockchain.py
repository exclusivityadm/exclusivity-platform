from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
import os

# ❌ NO prefix here — mounted in main.py
router = APIRouter(tags=["blockchain"])

# Default configuration
BASE_EXPLORER = "https://mainnet.base.org"
BASE_RPC = "https://mainnet.base.org/api"
CHAIN_ID_DECIMAL = 8453
CHAIN_ID_HEX = hex(CHAIN_ID_DECIMAL)


@router.get("/status")
async def blockchain_status():
    """Basic blockchain connectivity and network status check."""
    try:
        # Optionally test API connectivity
        response = requests.get(BASE_EXPLORER, timeout=5)
        ok = response.status_code == 200

        return JSONResponse(
            content={
                "connected": ok,
                "network": "Base Mainnet",
                "chain_id_decimal": CHAIN_ID_DECIMAL,
                "chain_id_hex": CHAIN_ID_HEX,
                "explorer": BASE_EXPLORER,
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"connected": False, "error": str(e)},
        )
