import json
from collections.abc import Sequence
from typing import Any

from app.core.config import settings
from app.core.exceptions import ConfigurationError, RepositoryError


class UserReviewEmbeddingRepository:
    REVIEW_TABLE = "user_reviews"
    USER_ID_COLUMN = "user_id"
    EMBEDDING_COLUMN = "review_embedding"

    def __init__(self, database: Any | None = None):
        if database is None:
            raise ConfigurationError(
                "UserReviewEmbeddingRepository requires a database client."
            )
        self.database = database

    async def find_by_user_id(self, user_id: str) -> list[list[float]]:
        try:
            response = (
                await self.database.from_(self.REVIEW_TABLE)
                .select(self.EMBEDDING_COLUMN)
                .eq(self.USER_ID_COLUMN, user_id)
                .not_
                .is_(self.EMBEDDING_COLUMN, "null")
                .execute()
            )
            return self._parse_embeddings(response.data or [])
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc

    def _parse_embeddings(self, rows: list[dict[str, Any]]) -> list[list[float]]:
        return [
            embedding
            for row in rows
            if (
                embedding := self._parse_embedding(row.get(self.EMBEDDING_COLUMN))
            ) is not None
        ]

    def _parse_embedding(self, value: Any) -> list[float] | None:
        # Supabase/pgvector 응답은 클라이언트 직렬화 경로에 따라 list 또는 JSON
        # 문자열로 올 수 있으므로, repository 경계에서 내부 타입과 차원을 확정한다.
        if value is None:
            return None

        if isinstance(value, str):
            value = json.loads(value)

        if isinstance(value, (bytes, bytearray, str)) or not isinstance(
            value, Sequence
        ):
            raise ValueError("review embedding must be a sequence of numbers.")

        embedding = [float(item) for item in value]
        if len(embedding) != settings.EMBEDDING_DIMENSIONS:
            raise ValueError("review embedding has invalid dimensions.")

        return embedding
