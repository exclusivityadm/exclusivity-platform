from fastapi import APIRouter
router = APIRouter()

@router.get("")
def tokens_summary():
    return {"total_supply": 1000000, "minted_today": 1200, "holders": 324}
