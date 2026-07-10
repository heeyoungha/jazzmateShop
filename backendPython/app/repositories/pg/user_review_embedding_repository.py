import json
from collections.abc import Sequence

from app.core.config import settings
from app.core.exceptions import RepositoryError


class PgUserReviewEmbeddingRepository:
    def __init__(self, pool):
        self.pool = pool

    async def find_by_user_id(self, user_id: str) -> list[list[float]]:
        sql = """
            SELECT review_embedding::text
            FROM user_reviews
            WHERE user_id = $1
              AND review_embedding IS NOT NULL
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql, user_id)
            return [e for row in rows if (e := self._parse(row[0])) is not None]
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc

    def _parse(self, value) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = json.loads(value)
        if isinstance(value, (bytes, bytearray)) or not isinstance(value, Sequence):
            return None
        embedding = [float(x) for x in value]
        if len(embedding) != settings.EMBEDDING_DIMENSIONS:
            return None
        return embedding
