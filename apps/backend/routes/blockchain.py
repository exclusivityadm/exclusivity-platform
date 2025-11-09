# apps/backend/routes/blockchain.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/blockchain", tags=["Blockchain"])
async def test_blockchain():
    """Placeholder route for blockchain features."""
    return {"status": "ok", "source": "blockchain route active"}
