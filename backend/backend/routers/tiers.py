from fastapi import APIRouter
router = APIRouter()

@router.get("")
def list_tiers():
    return [
        {"tier_name":"Tier 1","min_tokens":0,"perks":["Welcome badge"],"color_theme":"#6EE7B7"},
        {"tier_name":"Tier 2","min_tokens":500,"perks":["Free shipping"],"color_theme":"#93C5FD"},
        {"tier_name":"Tier 3","min_tokens":1500,"perks":["VIP access"],"color_theme":"#FCA5A5"},
    ]
