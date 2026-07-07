class EmbeddingService:
    def __init__(self) -> None:
        self.name = "embedding-service"

    def create_embedding(self, text: str) -> list[float]:
        return [0.0, 0.0, 1.0] if text else []
