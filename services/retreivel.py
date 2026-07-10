from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from .embeddings import get_embedding
except ImportError:  # pragma: no cover - allows direct script execution
    from embeddings import get_embedding


def retrieve_chunks(query: str, document_id: int, db: Session, limit: int = 7) -> List[Dict[str, Any]]:
    """Hybrid retrieval: combines vector similarity search with full-text keyword
    search, deduplicates results, and returns the top unique chunks.

    Args:
        query:       The user's question / search string.
        document_id: ID of the document to search — restricts both queries to a
                     single document so results never bleed across users.
        db:          An active SQLAlchemy database session.
        limit:       Maximum number of unique chunks to return (default 7).

    Returns:
        A list of dicts with keys ``id``, ``content``, and ``page_number``.
    """

    # Step 1 — embed the user's question
    query_vector = get_embedding(query)

    # Step 2 — vector search: rank chunks by cosine distance to the query embedding
    vector_rows = db.execute(
        text("""
            SELECT id, content, page_number
            FROM document_chunks
            WHERE document_id = :doc_id
            ORDER BY embedding <=> CAST(:query_vector AS vector)
            LIMIT 5
        """),
        {"query_vector": query_vector, "doc_id": document_id},
    ).fetchall()

    # Step 3 — keyword search: full-text search using PostgreSQL plainto_tsquery
    keyword_rows = db.execute(
        text("""
            SELECT id, content, page_number
            FROM document_chunks
            WHERE document_id = :doc_id
            AND to_tsvector('english', content) @@ plainto_tsquery('english', :query)
            LIMIT 5
        """),
        {"query": query, "doc_id": document_id},
    ).fetchall()

    # Step 4 — merge both result sets and deduplicate by chunk id
    seen_ids: set[int] = set()
    unique_chunks: List[Dict[str, Any]] = []

    for row in list(vector_rows) + list(keyword_rows):
        if row.id not in seen_ids:
            seen_ids.add(row.id)
            unique_chunks.append(
                {
                    "id": row.id,
                    "content": row.content,
                    "page_number": row.page_number,
                }
            )

    # Step 5 — return top 5-7 unique chunks with content and page_number
    return unique_chunks[:limit]
