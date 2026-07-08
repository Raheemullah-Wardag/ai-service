from services.llm import stream_chat_response, get_chat_response
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.llm import stream_chat_response
from pydantic import BaseModel

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]

@router.post("/stream")
async def chat_stream(body: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    
    return StreamingResponse(
        stream_chat_response(messages),
        media_type="text/event-stream"
    )
@router.post("/")
async def chat(body: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    response = get_chat_response(messages)
    return {"response": response}