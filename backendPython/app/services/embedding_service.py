from typing import Any, List

from app.core.config import settings
from app.core.exceptions import ConfigurationError, EmbeddingError


class EmbeddingService:
    def __init__(self, openai_client: Any):
        if openai_client is None:
            raise ConfigurationError("EmbeddingService requires an openai client.")
        self.openai_client = openai_client

    async def embed_review(self, review_content: str) -> List[float]:
        try:
            response = await self.openai_client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=review_content,
            )
            return list(response.data[0].embedding)
        except Exception as exc:
            raise EmbeddingError(str(exc)) from exc
