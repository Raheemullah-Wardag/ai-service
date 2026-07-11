from fastapi import FastAPI
from dotenv import load_dotenv
from routers import chat, documents
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="AI Service", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])

@app.get("/")
def health():
    return {"status": "AI service running"}