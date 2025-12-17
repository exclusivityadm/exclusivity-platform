"""
AI Context Builder (Canonical)
==============================

Purpose:
- Build a consistent, policy-driven context for Orion/Lyric (merchant copilots).
- Avoid crypto terms; use points/badges language.
- Produce structured context that can be logged safely and used for deterministic prompting.

This module does NOT:
- Call the LLM
- Read/write the DB directly

Instead it accepts already-fetched objects/dicts from your services/routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal


Persona = Literal["orion", "lyric"]


@dataclass(frozen=True)
class AIContext:
    persona: Persona
    system_prompt: str
    developer_notes: str
    merchant_context: Dict[str, Any]
    program_context: Dict[str, Any]
    request_context: Dict[str, Any]
    safety_context: Dict[str, Any]

    def to_messages(self, user_message: str) -> List[Dict[str, str]]:
        """
        OpenAI-style messages payload.
        """
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "developer", "content": self.developer_notes},
            {
                "role": "user",
                "content": (
                    f"{user_message}\n\n"
                    f"---\n"
                    f"MERCHANT_CONTEXT:\n{self.merchant_context}\n\n"
                    f"PROGRAM_CONTEXT:\n{self.program_context}\n\n"
                    f"REQUEST_CONTEXT:\n{self.request_context}\n\n"
                    f"SAFETY_CONTEXT:\n{self.safety_context}\n"
                ),
            },
        ]


class AIContextBuilder:
    """
    Canonical builder for merchant-copilot context.
    """

    def build(
        self,
        *,
        persona: Persona,
        merchant: Dict[str, Any],
        program: Dict[str, Any],
        request_meta: Optional[Dict[str, Any]] = None,
        now_utc: Optional[datetime] = None,
    ) -> AIContext:
        now_utc = now_utc or datetime.utcnow()
        request_meta = request_meta or {}

        # System prompt: persona voice + prime directives
        system_prompt = self._system_prompt(persona=persona)

        # Developer notes: stable behavioral constraints (non-punitive, cooperative)
        developer_notes = self._developer_notes()

        merchant_context = self._merchant_context(merchant, now_utc=now_utc)
        program_context = self._program_context(program)
        request_context = self._request_context(request_meta, now_utc=now_utc)

        safety_context = {
            "language_policy": {
                "avoid_terms": ["token", "nft", "wallet", "crypto", "blockchain", "gas"],
                "use_terms": ["points", "badges", "tiers", "members"],
                "rule": "Only discuss on-chain implementation if merchant explicitly asks, and still use plain language.",
            },
            "tone_policy": {
                "non_punitive": True,
                "transparent_limits": True,
                "graceful_degradation": True,
                "cooperative": True,
            },
            "data_policy": {
                "secrets": "Never request or expose API keys, private keys, service role keys, or raw auth tokens.",
                "pii": "Keep outputs minimal; summarize. Do not echo customer emails/addresses unless necessary.",
            },
        }

        return AIContext(
            persona=persona,
            system_prompt=system_prompt,
            developer_notes=developer_notes,
            merchant_context=merchant_context,
            program_context=program_context,
            request_context=request_context,
            safety_context=safety_context,
        )

    def _system_prompt(self, *, persona: Persona) -> str:
        if persona == "orion":
            voice = (
                "You are Orion — a calm, decisive, systems-minded merchant copilot. "
                "You speak clearly and focus on profitable, practical actions."
            )
        else:
            voice = (
                "You are Lyric — a warm, insightful, creative merchant copilot. "
                "You speak clearly and help the merchant feel confident and supported."
            )

        return (
            f"{voice}\n\n"
            "Your mission:\n"
            "- Help the merchant grow revenue and retention with transparent, ethical UX.\n"
            "- Optimize pricing and loyalty design using points/badges/tiers language.\n"
            "- Never be punitive. When limits exist, explain them neutrally and offer alternatives.\n"
            "- Be concise, actionable, and avoid technical jargon unless asked.\n"
        )

    def _developer_notes(self) -> str:
        return (
            "Behavior rules (canonical):\n"
            "1) No scolding. No threats. No coercive upsell.\n"
            "2) If something is not possible, say what is possible.\n"
            "3) Prefer step-by-step options with tradeoffs.\n"
            "4) Avoid crypto terms; say points/badges.\n"
            "5) When uncertain, ask for the missing variable ONLY if required; otherwise make a reasonable assumption and state it.\n"
        )

    def _merchant_context(self, merchant: Dict[str, Any], *, now_utc: datetime) -> Dict[str, Any]:
        # Only keep what the model needs.
        return {
            "merchant_id": merchant.get("id") or merchant.get("merchant_id"),
            "store_name": merchant.get("store_name") or merchant.get("name"),
            "platform": merchant.get("platform", "shopify"),
            "currency": merchant.get("currency", "USD"),
            "timezone": merchant.get("timezone", "America/New_York"),
            "goals": merchant.get("goals", ["growth", "retention", "margin"]),
            "brand_voice": merchant.get("brand_voice", "luxury"),
            "now_utc": now_utc.isoformat() + "Z",
        }

    def _program_context(self, program: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "program_name": program.get("program_name", "Exclusivity"),
            "tiers": program.get("tiers", []),
            "points_label": program.get("points_label", "points"),
            "badges_label": program.get("badges_label", "badges"),
            "earning_rules": program.get("earning_rules", {}),
            "redemption_rules": program.get("redemption_rules", {}),
            "pricing_policy": program.get("pricing_policy", {}),
            "disclosure_policy": program.get(
                "disclosure_policy",
                {
                    "default": "silent",
                    "note": "Program is not public-facing unless merchant chooses to disclose.",
                },
            ),
        }

    def _request_context(self, request_meta: Dict[str, Any], *, now_utc: datetime) -> Dict[str, Any]:
        return {
            "request_id": request_meta.get("request_id"),
            "route": request_meta.get("route"),
            "ip_hash": request_meta.get("ip_hash"),
            "user_agent": request_meta.get("user_agent"),
            "now_utc": now_utc.isoformat() + "Z",
        }
