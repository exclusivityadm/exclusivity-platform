from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from ..config import env

router = APIRouter()
client = OpenAI(api_key=env("OPENAI_API_KEY"))

class StartIn(BaseModel):
    agent: str = "orion"
    message: str

class ChatIn(BaseModel):
    conversation_id: str
    message: str
    agent: str = "orion"

@router.get("/status")
def status():
    return {"ok": True, "agents": ["orion","lyric"]}

@router.post("/start")
def start_chat(body: StartIn):
    try:
        model = env("AI_MODEL_GPT", "gpt-5")
        system = "You are an AI assistant for a loyalty platform. Be concise and helpful."
        if body.agent.lower() == "lyric":
            system = "You are Lyric, a warm, empathetic brand voice. Be encouraging and creative."
        resp = client.responses.create(
            model=model,
            input=[
                {"role":"system","content":system},
                {"role":"user","content":body.message},
            ],
        )
        answer = resp.output_text
        return {"conversation_id":"conv_" + body.agent, "agent": body.agent, "reply": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {e}")

@router.post("/chat")
def continue_chat(body: ChatIn):
    try:
        model = env("AI_MODEL_GPT", "gpt-5")
        resp = client.responses.create(
            model=model,
            input=[{"role":"user","content":body.message}],
        )
        return {"conversation_id": body.conversation_id, "reply": resp.output_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {e}")
