# apps/backend/core/context.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class KillSwitches:
    global_pause: bool = False
    ai_pause: bool = False
    loyalty_pause: bool = False
    shopify_pause: bool = False


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    merchant_id: Optional[str]
    shop_domain: Optional[str]

    # actor identity
    actor_type: str               # "merchant" | "admin" | "internal" | "unknown"
    actor_id: Optional[str]       # merchant_id or admin_id, etc.
    auth_source: str              # "shopify" | "admin" | "internal" | "none"

    kill_switches: KillSwitches
    started_at_ms: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "merchant_id": self.merchant_id,
            "shop_domain": self.shop_domain,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "auth_source": self.auth_source,
            "kill_switches": {
                "global_pause": self.kill_switches.global_pause,
                "ai_pause": self.kill_switches.ai_pause,
                "loyalty_pause": self.kill_switches.loyalty_pause,
                "shopify_pause": self.kill_switches.shopify_pause,
            },
            "started_at_ms": self.started_at_ms,
        }
