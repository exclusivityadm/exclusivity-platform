"""
Universal silent patch for Supabase Realtime + websockets>=12 compatibility.
Completely suppresses 'cannot import name ClientConnection' errors.
"""

import sys
import types
import importlib

try:
    import websockets
except Exception as e:
    print("[Patch] websockets not installed:", e)
    websockets = types.ModuleType("websockets")

# --- 1️⃣ Ensure async module hierarchy exists ---
if not hasattr(websockets, "asyncio"):
    websockets.asyncio = types.ModuleType("websockets.asyncio")

# --- 2️⃣ Attempt to bind a valid client submodule ---
try:
    # modern (>=12)
    client_mod = importlib.import_module("websockets.client")
except ModuleNotFoundError:
    try:
        # legacy (<12)
        client_mod = importlib.import_module("websockets.legacy.client")
    except Exception:
        # final fallback: dummy interface
        class DummyClient:
            async def connect(self, *_, **__):
                raise RuntimeError("websockets client unavailable")

        client_mod = types.ModuleType("websockets.legacy.client")
        client_mod.ClientConnection = DummyClient

# --- 3️⃣ Register patched submodules globally ---
websockets.asyncio.client = client_mod
sys.modules["websockets.asyncio"] = websockets.asyncio
sys.modules["websockets.asyncio.client"] = client_mod
sys.modules["websockets.legacy.client"] = client_mod

print("[Patch] websockets async client patch loaded successfully.")
