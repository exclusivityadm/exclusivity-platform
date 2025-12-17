from web3 import Web3
from apps.backend.config.chain import (
    CHAIN_ENABLED,
    ALCHEMY_BASE_HTTP,
    BASE_CHAIN_ID,
)

def get_w3() -> Web3:
    if not CHAIN_ENABLED:
        raise RuntimeError("Chain disabled")
    if not ALCHEMY_BASE_HTTP:
        raise RuntimeError("Missing ALCHEMY_BASE_HTTP")
    w3 = Web3(Web3.HTTPProvider(ALCHEMY_BASE_HTTP))
    if not w3.is_connected():
        raise RuntimeError("Base RPC not connected")
    if w3.eth.chain_id != BASE_CHAIN_ID:
        raise RuntimeError("Unexpected chain id")
    return w3
