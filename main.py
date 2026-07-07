from fastapi import FastAPI
from dotenv import load_dotenv
from routers import chat, documents

load_dotenv()

app = FastAPI(title="AI Service", version="1.0.0")

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])

@app.get("/")
def health():
    return {"status": "AI service running"}