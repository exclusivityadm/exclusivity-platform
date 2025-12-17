from typing import Dict, Any, Optional
import os

# NOTE: EXCL-AI-01 hardens behavior and structure.
# Actual model provider can be wired later (or already exists elsewhere in your repo).
# This module fails closed if not configured, rather than returning misleading output.

class AIRuntimeError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

def is_configured() -> bool:
    # Support whichever env you already use; add more keys later if needed.
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY"))

def generate_reply(system_prompt: str, user_text: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Placeholder “model call” function.
    - If your repo already has an AI client, we will swap this implementation to call it.
    - For now, fail closed if no provider key exists.
    """
    if not is_configured():
        raise AIRuntimeError("AI provider not configured (missing API key).", 501)

    # If you already have an internal AI client, we will integrate it here once we see your current routes/ai.py.
    # This placeholder prevents silent wrong behavior.
    raise AIRuntimeError("AI runtime wiring not installed yet for this repo.", 501)
