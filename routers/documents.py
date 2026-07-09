from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db
from services.document_processor import process_document, validate_pdf
from services.embeddings import get_batch_embeddings
import asyncio

router = APIRouter()
MAX_FILE_SIZE = 5 * 1024 * 1024

@router.post("/upload")
async def upload_document(
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
    loop = asyncio.get_event_loop()
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