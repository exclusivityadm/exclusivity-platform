# =====================================================
# 💠 Exclusivity Backend - Blockchain & Analytics Routes
# =====================================================

from fastapi import APIRouter, HTTPException
import os
import requests
import json

router = APIRouter()

# -----------------------------------------------------
# 🌐 Blockchain Environment Validation
# -----------------------------------------------------
def get_chain_config():
    return {
        "BASE_RPC_URL": os.getenv("BASE_RPC_URL"),
        "COINBASE_API_KEY": bool(os.getenv("COINBASE_API_KEY")),
        "BASE_WALLET_ADDRESS": os.getenv("BASE_WALLET_ADDRESS"),
        "DEV_FEE_WALLET": os.getenv("DEV_FEE_WALLET"),
        "BRAND_WALLET": os.getenv("BRAND_WALLET"),
        "ENABLE_MINTING": os.getenv("ENABLE_MINTING"),
        "ENABLE_TOKEN_AESTHETICS": os.getenv("ENABLE_TOKEN_AESTHETICS"),
        "COINBASE_NETWORK": os.getenv("COINBASE_NETWORK"),
        "COINBASE_DOMAIN_ALLOWLIST": os.getenv("COINBASE_DOMAIN_ALLOWLIST"),
    }

# -----------------------------------------------------
# 🔗 Route: Blockchain Connection Test
# -----------------------------------------------------
@router.get("/chain-status", tags=["analytics"])
def chain_status():
    """
    Confirms connectivity to Base RPC node and validates environment setup.
    Returns ping latency and key settings.
    """
    config = get_chain_config()
    base_rpc = config["BASE_RPC_URL"]
    if not base_rpc:
        raise HTTPException(status_code=500, detail="BASE_RPC_URL not set in environment")

    try:
        # Perform a lightweight 'eth_chainId' RPC call
        headers = {"Content-Type": "application/json"}
        payload = {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}
        response = requests.post(base_rpc, headers=headers, data=json.dumps(payload), timeout=8)

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"RPC error: {response.text}")

        data = response.json()
        return {
            "connected": True,
            "chain_id_hex": data.get("result"),
            "chain_id_decimal": int(data.get("result"), 16) if data.get("result") else None,
            "minting_enabled": config["ENABLE_MINTING"],
            "aesthetics_enabled": config["ENABLE_TOKEN_AESTHETICS"],
            "wallets": {
                "brand_wallet": config["BRAND_WALLET"],
                "developer_wallet": config["DEV_FEE_WALLET"],
            },
            "coinbase_network": config["COINBASE_NETWORK"],
            "domain_allowlist": config["COINBASE_DOMAIN_ALLOWLIST"],
        }

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout contacting Base RPC node")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chain check failed: {str(e)}")

# -----------------------------------------------------
# 📊 Route: System Diagnostic Summary
# -----------------------------------------------------
@router.get("/system-summary", tags=["analytics"])
def system_summary():
    """
    Returns a structured overview of backend system configuration.
    Useful for verifying all integration layers are visible to the runtime.
    """
    summary = {
        "version": os.getenv("APP_VERSION", "unknown"),
        "environment": os.getenv("APP_ENV", "unknown"),
        "debug_mode": os.getenv("DEBUG_MODE", "false"),
        "supabase_url": os.getenv("SUPABASE_URL"),
        "base_rpc_url": os.getenv("BASE_RPC_URL"),
        "elevenlabs_key": bool(os.getenv("ELEVENLABS_API_KEY")),
        "openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "shopify_connected": bool(os.getenv("SHOPIFY_ACCESS_TOKEN")),
        "render_service": os.getenv("RENDER_SERVICE_NAME"),
        "vercel_project": os.getenv("VERCEL_PROJECT_NAME"),
    }
    return {"system": summary}
