from typing import Dict, Any

BANNED_TERMS = {
    "nft", "token", "mint", "gas", "wallet", "blockchain", "web3",
}

def sanitize_user_text(text: str) -> str:
    # Lightweight normalization (no destructive filtering)
    return (text or "").strip()

def enforce_language(text: str) -> str:
    # Replace banned terms with merchant-friendly equivalents (minimal intervention)
    out = text
    for term in BANNED_TERMS:
        out = out.replace(term, "points")
        out = out.replace(term.upper(), "POINTS")
        out = out.replace(term.capitalize(), "Points")
    return out

def response_envelope(persona: str, reply: str, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "ok": True,
        "persona": persona,
        "reply": reply,
        "meta": meta or {},
    }
