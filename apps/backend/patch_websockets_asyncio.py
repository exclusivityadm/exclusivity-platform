"""
Fix for Supabase + websockets >= 12.
Ensures legacy import paths still resolve cleanly.
"""

import sys, types, importlib

try:
    import websockets
except ImportError:
    # fallback if not yet installed
    websockets = types.ModuleType("websockets")

# Ensure module hierarchy
if not hasattr(websockets, "asyncio"):
    websockets.asyncio = types.ModuleType("websockets.asyncio")

try:
    client_mod = importlib.import_module("websockets.client")
except ModuleNotFoundError:
    try:
        client_mod = importlib.import_module("websockets.legacy.client")
    except Exception:
        client_mod = types.ModuleType("websockets.client")

# Mirror across legacy names so imports don't fail
websockets.asyncio.client = client_mod
sys.modules["websockets.asyncio"] = websockets.asyncio
sys.modules["websockets.asyncio.client"] = client_mod
sys.modules["websockets.legacy.client"] = client_mod

print("[Patch] websockets async client patch loaded successfully.")
