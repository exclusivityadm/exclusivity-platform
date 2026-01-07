# apps/backend/services/action_router.py
# =====================================================
# AI Action Router — Canonical Execution Surface
# =====================================================

from typing import Dict, Any

def preview_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preview mode — advisory only.
    No side effects. No writes.
    """
    return {
        "ok": True,
        "mode": "preview",
        "action": action,
        "message": "This is a preview. No actions have been executed.",
        "would_execute": True,
    }

def execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute mode — called only after entitlement check.
    This is the canonical execution surface.
    
    NOTE:
    - For now, execution is acknowledged and logged by AI layer.
    - Concrete execution (pricing apply, mint enqueue, marketing blast)
      will be wired here later WITHOUT touching ai.py.
    """
    return {
        "ok": True,
        "mode": "execute",
        "action": action,
        "message": "Action accepted for execution.",
        "executed": True,
    }
