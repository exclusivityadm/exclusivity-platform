from typing import Dict, Any, Optional

from apps.backend.services.ai.prompts import ORION_SYSTEM, LYRIC_SYSTEM
from apps.backend.services.ai.guardrails import sanitize_user_text, enforce_language, response_envelope
from apps.backend.services.ai.runtime import generate_reply, AIRuntimeError

def chat(persona: str, user_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cleaned = sanitize_user_text(user_text)
    cleaned = enforce_language(cleaned)

    system = ORION_SYSTEM if persona.lower() == "orion" else LYRIC_SYSTEM

    try:
        reply = generate_reply(system_prompt=system, user_text=cleaned, context=context)
        reply = enforce_language(reply)
        return response_envelope(persona=persona, reply=reply, meta={"hardened": True})
    except AIRuntimeError as e:
        # Fail closed, but still structured and transparent.
        return {
            "ok": False,
            "error": "ai_not_ready",
            "message": e.message,
            "status_code": e.status_code,
        }
