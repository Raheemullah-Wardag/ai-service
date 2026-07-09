import io
from typing import Any, Dict, List

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def is_valid_pdf(file_bytes: bytes) -> bool:
    """Check the PDF magic bytes."""
    return len(file_bytes) >= 4 and file_bytes[:4] == b"%PDF"


def validate_pdf(file_bytes: bytes, filename: str | None = None) -> None:
    """Validate uploaded file type and PDF signature before processing."""
    if filename is None:
        filename = ""

    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only .pdf files are supported")

    if not is_valid_pdf(file_bytes):
        raise ValueError("File content does not match a PDF signature")

    try:
        PdfReader(io.BytesIO(file_bytes))
    except (PdfReadError, ValueError, TypeError) as exc:
        raise ValueError("The uploaded PDF could not be parsed") from exc


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += chunk_size - overlap

    return chunks


def process_document(
    file_bytes: bytes,
    filename: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> List[Dict[str, Any]]:
    """Extract text from a PDF page by page and split it into overlapping chunks."""
    validate_pdf(file_bytes, filename)

    reader = PdfReader(io.BytesIO(file_bytes))
    chunks: List[Dict[str, Any]] = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if not page_text.strip():
            continue

        page_chunks = _chunk_text(page_text, chunk_size=chunk_size, overlap=overlap)
        for chunk_index, content in enumerate(page_chunks):
            chunks.append(
                {
                    "content": content.strip(),
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                }
            )

    return chunks
