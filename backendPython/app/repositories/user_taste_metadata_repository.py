from typing import Any

from app.core.exceptions import ConfigurationError, RepositoryError
from app.repositories.album_metadata_parsers import parse_genres, parse_year
from app.schemas.recommendation import AlbumMetadata


class UserTasteMetadataRepository:
    REVIEW_TABLE = "user_reviews"
    ALBUM_TABLE = "mb_album"
    USER_ID_COLUMN = "user_id"
    REVIEW_ALBUM_ID_COLUMN = "mb_album_gid"
    ALBUM_ID_COLUMN = "gid"
    ALBUM_COLUMNS = "gid,artist_name,genres,first_release_year"

    def __init__(self, database: Any | None = None):
        if database is None:
            raise ConfigurationError(
                "UserTasteMetadataRepository requires a database client."
            )
        self.database = database

    def find_by_user_id(self, user_id: str) -> list[AlbumMetadata]:
        try:
            review_response = (
                self.database.from_(self.REVIEW_TABLE)
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
                self.database.from_(self.ALBUM_TABLE)
                .select(self.ALBUM_COLUMNS)
                .in_(self.ALBUM_ID_COLUMN, album_ids)
                .execute()
            )
            return [self._parse_album(row) for row in album_response.data or []]
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

    def _parse_album(self, row: dict[str, Any]) -> AlbumMetadata:
        return AlbumMetadata(
            album_id=str(row.get(self.ALBUM_ID_COLUMN)),
            artist_name=row.get("artist_name"),
            genres=parse_genres(row.get("genres")),
            first_release_year=parse_year(row.get("first_release_year")),
        )
