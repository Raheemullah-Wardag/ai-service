from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from db.database import get_db
from cache.redis_client import redis_client
from services.document_processor import process_document, validate_pdf
from services.embeddings import get_batch_embeddings
from services.retreivel import retrieve_chunks
from services.llm import stream_chat_response
from dependencies import limiter
import asyncio
import json
router = APIRouter()
MAX_FILE_SIZE = 5 * 1024 * 1024

@router.post("/upload")
@limiter.limit("20/minute")
async def upload_document(
    request: Request, 
    user_id: int,
    conversation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    print("Step 1: Reading file")
    file_bytes = await file.read()
    
    print(f"Step 2: Size - {len(file_bytes)} bytes")
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5MB")
    
    print("Step 3: Validating PDF")
    try:
        validate_pdf(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    print("Step 4: Processing chunks")
    chunks = process_document(file_bytes, file.filename)
    print(f"Step 4 done: {len(chunks)} chunks")
    
    if not chunks:
        raise HTTPException(status_code=400, detail="No text extracted")
    
    print("Step 5: Saving document record")
    doc_result = db.execute(
        text("INSERT INTO documents (user_id, filename) VALUES (:user_id, :filename) RETURNING id"),
        {"user_id": user_id, "filename": file.filename}
    )
    document_id = doc_result.fetchone()[0]
    db.commit()
    print(f"Step 5 done: document_id={document_id}")
    
    print("Step 6: Generating embeddings")
    texts = [chunk["content"] for chunk in chunks]
    loop = asyncio.get_running_loop()
    embeddings = await loop.run_in_executor(None, get_batch_embeddings, texts)
    print(f"Step 6 done: {len(embeddings)} embeddings")
    
    print("Step 7: Bulk inserting chunks")
    db.execute(
        text("""
            INSERT INTO document_chunks (document_id, content, page_number, embedding)
            VALUES (:doc_id, :content, :page_num, :embedding)
        """),
        [
            {
                "doc_id": document_id,
                "content": chunks[i]["content"],
                "page_num": chunks[i]["page_number"],
                "embedding": embeddings[i]
            }
            for i in range(len(chunks))
        ]
    )
    db.commit()
    print("Step 7 done")
    
    return {
        "message": "Document uploaded successfully",
        "document_id": document_id,
        "chunks_processed": len(chunks)
    }




class RAGChatRequest(BaseModel):
    conversation_id: int
    user_id: int
    document_id: int
    message: str

@router.post("/chat")
@limiter.limit("20/minute")
async def rag_chat(request: Request, body: RAGChatRequest, db: Session = Depends(get_db)):
    
    # 1. Retrieve relevant chunks using hybrid search
    loop = asyncio.get_running_loop()
    chunks = await loop.run_in_executor(
        None, retrieve_chunks, body.message, body.document_id, db
    )
    
    # 2. Build context from chunks with citations
    context = "\n\n".join([
        f"[Page {c['page_number']}]: {c['content']}"
        for c in chunks
    ])
    
    # 3. Fetch conversation history from Redis/DB
    cache_key = f"ai_chat:{body.conversation_id}"
    cached = redis_client.lrange(cache_key, 0, -1)
    history = [json.loads(m) for m in cached] if cached else []
    
    # 4. Build RAG prompt
    rag_prompt = f"""You are a helpful assistant answering questions about a document.

Use ONLY the following document excerpts to answer. Always cite the page number.
If the answer is not in the excerpts, say "I cannot find this information in the document."

Document excerpts:
{context}

Question: {body.message}"""
    
    # 5. Append RAG prompt to history
    messages = history + [{"role": "user", "content": rag_prompt}]
    
    # 6. Save original user message to DB
    db.execute(
        text("INSERT INTO messages (conversation_id, role, content) VALUES (:conv_id, 'user', :content)"),
        {"conv_id": body.conversation_id, "content": body.message}
    )
    db.commit()
    
    # 7. Stream response and save to DB
    full_response = []
    
    async def generate_and_save():
        async for chunk in stream_chat_response(messages):
            full_response.append(chunk)
            yield chunk
        
        ai_response = "".join(full_response)
        db.execute(
            text("INSERT INTO messages (conversation_id, role, content) VALUES (:conv_id, 'assistant', :content)"),
            {"conv_id": body.conversation_id, "content": ai_response}
        )
        db.commit()
        
        # Update Redis cache
        new_messages = history + [
            {"role": "user", "content": body.message},
            {"role": "assistant", "content": ai_response}
        ]
        redis_client.delete(cache_key)
        for msg in new_messages[-10:]:
            redis_client.rpush(cache_key, json.dumps(msg))
    
    return StreamingResponse(generate_and_save(), media_type="text/event-stream")