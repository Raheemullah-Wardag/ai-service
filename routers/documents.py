from fastapi import APIRouter

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/")
def upload_document() -> dict:
    return {"message": "Document upload endpoint ready"}
