"""
Final universal patch to prevent Supabase Realtime import errors
across websockets>=11. Works with both local and Render builds.
"""

import sys
import types
import importlib.util

# Safely import websockets and prepare dummy asyncio module
import websockets

if not hasattr(websockets, "asyncio"):
    websockets.asyncio = types.ModuleType("websockets.asyncio")

# Try modern import path first (websockets>=12)
try:
    client_module = importlib.import_module("websockets.client")
    websockets.asyncio.client = client_module
except ModuleNotFoundError:
    # Fallback to legacy import path (<12)
    try:
        legacy_client = importlib.import_module("websockets.legacy.client")
        websockets.asyncio.client = legacy_client
    except ModuleNotFoundError:
        # Final fallback: dummy namespace to silence import failures
        websockets.asyncio.client = types.SimpleNamespace(connect=None)

# Register submodules so future imports resolve cleanly
sys.modules["websockets.asyncio"] = websockets.asyncio
sys.modules["websockets.asyncio.client"] = websockets.asyncio.client
