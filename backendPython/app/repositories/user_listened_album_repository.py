import json
from collections.abc import Sequence
from typing import Any

from app.core.config import settings
from app.core.exceptions import ConfigurationError, RepositoryError


class UserListenedAlbumRepository:
    REVIEW_TABLE = "user_reviews"
    ALBUM_TABLE = "album_reference"
    USER_ID_COLUMN = "user_id"
    REVIEW_ALBUM_ID_COLUMN = "mb_album_gid"
    ALBUM_ID_COLUMN = "mb_release_group_id"
    EMBEDDING_COLUMN = "embedding"

    def __init__(self, database: Any | None = None):
        if database is None:
            raise ConfigurationError(
                "UserListenedAlbumRepository requires a database client."
            )
        self.database = database

    async def find_by_user_id(self, user_id: str) -> list[list[float]]:
        try:
            review_response = (
                await self.database.from_(self.REVIEW_TABLE)
                .select(self.REVIEW_ALBUM_ID_COLUMN)
                .eq(self.USER_ID_COLUMN, user_id)
                .not_
                .is_(self.REVIEW_ALBUM_ID_COLUMN, "null")
                .execute()
            )
            album_ids = self._distinct_album_ids(review_response.data or [])
            if not album_ids:
                return []

            album_response = (
                await self.database.from_(self.ALBUM_TABLE)
                .select(self.EMBEDDING_COLUMN)
                .in_(self.ALBUM_ID_COLUMN, album_ids)
                .not_
                .is_(self.EMBEDDING_COLUMN, "null")
                .execute()
            )

            return self._parse_embeddings(album_response.data or [])
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc

    def _distinct_album_ids(self, rows: list[dict[str, Any]]) -> list[str]:
        seen: set[str] = set()
        album_ids: list[str] = []
        for row in rows:
            album_id = row.get(self.REVIEW_ALBUM_ID_COLUMN)
            if album_id is None:
                continue
            album_id = str(album_id)
            if album_id not in seen:
                seen.add(album_id)
                album_ids.append(album_id)
        return album_ids

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
            raise ValueError("album embedding must be a sequence of numbers.")

        embedding = [float(item) for item in value]
        if len(embedding) != settings.EMBEDDING_DIMENSIONS:
            raise ValueError("album embedding has invalid dimensions.")

        return embedding
