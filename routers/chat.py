from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db
from cache.redis_client import redis_client
from services.llm import stream_chat_response, get_chat_response
from pydantic import BaseModel
import json

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    conversation_id: int
    user_id: int
    message: str

@router.post("/stream")
async def chat_stream(body: ChatRequest, db: Session = Depends(get_db)):
    cache_key = f"ai_chat:{body.conversation_id}"
    
    # 1. Try Redis cache first
    cached = redis_client.lrange(cache_key, 0, -1)
    
    if cached:
        messages = [json.loads(m) for m in cached]
    else:
        # 2. Cache miss - fetch from DB
        result = db.execute(
            text("""
                SELECT role, content FROM messages 
                WHERE conversation_id = :conv_id 
                ORDER BY created_at DESC 
                LIMIT 10
            """),
            {"conv_id": body.conversation_id}
        ).fetchall()
        
        messages = [{"role": r.role, "content": r.content} for r in reversed(result)]
    
    # 3. Save user message to DB
    db.execute(
        text("""
            INSERT INTO messages (conversation_id, role, content) 
            VALUES (:conv_id, 'user', :content)
        """),
        {"conv_id": body.conversation_id, "content": body.message}
    )
    db.commit()
    
    # 4. Append new user message to context
    messages.append({"role": "user", "content": body.message})
    
    # 5. Collect full response for saving
    full_response = []
    
    async def generate_and_save():
        async for chunk in stream_chat_response(messages):
            full_response.append(chunk)
            yield chunk
        
        # 6. Save AI response to DB
        ai_response = "".join(full_response)
        db.execute(
            text("""
                INSERT INTO messages (conversation_id, role, content)
                VALUES (:conv_id, 'assistant', :content)
            """),
            {"conv_id": body.conversation_id, "content": ai_response}
        )
        db.commit()
        
        # 7. Update Redis cache
        new_messages = messages + [{"role": "assistant", "content": ai_response}]
        redis_client.delete(cache_key)
        for msg in new_messages[-10:]:
            redis_client.rpush(cache_key, json.dumps(msg))
    
    return StreamingResponse(
        generate_and_save(),
        media_type="text/event-stream"
    )

@router.post("/")
async def chat(body: ChatRequest, db: Session = Depends(get_db)):
    messages = [{"role": body.role if hasattr(body, 'role') else "user", 
                 "content": body.message}]
    response = get_chat_response(messages)
    return {"response": response}