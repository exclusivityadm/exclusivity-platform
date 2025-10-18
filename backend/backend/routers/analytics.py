from fastapi import APIRouter
router = APIRouter()

@router.get("")
def analytics_summary():
    return {
        "visits_7d": 4219,
        "redemptions_7d": 312,
        "avg_order_value": 72.43,
        "conversion_rate": 0.034,
    }
