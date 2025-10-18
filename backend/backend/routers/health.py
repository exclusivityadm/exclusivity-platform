from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {"status":"ok","message":"Exclusivity backend (FastAPI, Python 3.13-ready)"}

@router.get("/")
def root():
    return {"app":"Exclusivity","api":"v1","ok":True}
