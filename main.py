from fastapi import FastAPI
from dotenv import load_dotenv
from dependencies import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from routers import chat, documents

load_dotenv()


app = FastAPI(title="AI Service", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])

@app.get("/")
def health():
    return {"status": "AI service running"}