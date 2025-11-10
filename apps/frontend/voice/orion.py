from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os

router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/orion")
async def generate_orion(request: Request):
    data = await request.json()
    text = data.get("text", "")
    # TODO: Integrate ElevenLabs Orion voice here
    return JSONResponse({"status": "ok", "speaker": "orion", "text": text})
