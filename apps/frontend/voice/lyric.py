from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os

router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/lyric")
async def generate_lyric(request: Request):
    data = await request.json()
    text = data.get("text", "")
    # TODO: Integrate ElevenLabs Lyric voice here
    return JSONResponse({"status": "ok", "speaker": "lyric", "text": text})
