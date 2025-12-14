from __future__ import annotations

from typing import Dict, Any


class LoyaltyService:
    def __init__(self, repo):
        self.repo = repo

    async def get_policy(self, merchant_id: str):
        return await self.repo.get_policy(merchant_id)

    async def upsert_policy(self, merchant_id: str, policy: Dict[str, Any]):
        return await self.repo.upsert_policy(merchant_id, policy)

    async def get_member_status(self, merchant_id: str, member_ref: str):
        return await self.repo.get_member_status(merchant_id, member_ref)

    async def award_for_order(self, **kwargs):
        return {"ok": True}

    async def adjust_for_refund(self, **kwargs):
        return {"ok": True}
