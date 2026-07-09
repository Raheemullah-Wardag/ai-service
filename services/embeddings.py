from dotenv import load_dotenv
from google.genai import types
try:
    from .llm import client
except ImportError:  # pragma: no cover - allows direct script execution
    from llm import client

load_dotenv()


class EmbeddingService:
    def __init__(self) -> None:
        self.name = "embedding-service"

    def create_embedding(self, text: str) -> list[float]:
        return get_embedding(text)


def get_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the provided text."""
    if not text or not text.strip():
        raise ValueError("Text must not be empty")

    result = client.models.embed_content(
    model="gemini-embedding-001",
    contents=text,
    config=types.EmbedContentConfig(output_dimensionality=768)
    )
    
    return list(result.embeddings[0].values)
def get_batch_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in one API call."""
    if not texts:
        return []
    
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=768)
    )
    return [list(e.values) for e in result.embeddings]
if __name__ == "__main__":
    vector = get_embedding("Machine learning is a subset of artificial intelligence")
    print(f"Vector dimensions: {len(vector)}")
    print(f"First 5 values: {vector[:5]}")
