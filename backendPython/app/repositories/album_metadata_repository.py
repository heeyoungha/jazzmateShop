from typing import Any

from app.core.exceptions import ConfigurationError, RepositoryError
from app.repositories.album_metadata_parsers import parse_genres, parse_year
from app.schemas.recommendation import AlbumMetadata


class AlbumMetadataRepository:
    ALBUM_REFERENCE_TABLE = "album_reference"
    MB_ALBUM_TABLE = "mb_album"
    ALBUM_REFERENCE_ID_COLUMN = "id"
    RELEASE_GROUP_ID_COLUMN = "mb_release_group_id"
    MB_ALBUM_ID_COLUMN = "gid"
    MB_ALBUM_COLUMNS = "gid,artist_name,genres,first_release_year"

    def __init__(self, database: Any | None = None):
        if database is None:
            raise ConfigurationError(
                "AlbumMetadataRepository requires a database client."
            )
        self.database = database

    def find_by_album_reference_ids(
        self, album_reference_ids: list[str]
    ) -> dict[str, AlbumMetadata]:
        if not album_reference_ids:
            return {}

        try:
            reference_response = (
                self.database.from_(self.ALBUM_REFERENCE_TABLE)
                .select(f"{self.ALBUM_REFERENCE_ID_COLUMN},{self.RELEASE_GROUP_ID_COLUMN}")
                .in_(self.ALBUM_REFERENCE_ID_COLUMN, album_reference_ids)
                .not_
                .is_(self.RELEASE_GROUP_ID_COLUMN, "null")
                .execute()
            )
            release_group_by_reference_id = self._release_group_by_reference_id(
                reference_response.data or []
            )
            if not release_group_by_reference_id:
                return {}

            release_group_ids = list(dict.fromkeys(release_group_by_reference_id.values()))
            album_response = (
                self.database.from_(self.MB_ALBUM_TABLE)
                .select(self.MB_ALBUM_COLUMNS)
                .in_(self.MB_ALBUM_ID_COLUMN, release_group_ids)
                .execute()
            )
            metadata_by_release_group_id = {
                metadata.album_id: metadata
                for metadata in (
                    self._parse_album(row) for row in album_response.data or []
                )
            }
            return {
                reference_id: metadata_by_release_group_id[release_group_id]
                for reference_id, release_group_id in release_group_by_reference_id.items()
                if release_group_id in metadata_by_release_group_id
            }
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc

    def _release_group_by_reference_id(
        self, rows: list[dict[str, Any]]
    ) -> dict[str, str]:
        return {
            str(row[self.ALBUM_REFERENCE_ID_COLUMN]): str(row[self.RELEASE_GROUP_ID_COLUMN])
            for row in rows
            if row.get(self.ALBUM_REFERENCE_ID_COLUMN)
            and row.get(self.RELEASE_GROUP_ID_COLUMN)
        }

    def _parse_album(self, row: dict[str, Any]) -> AlbumMetadata:
        return AlbumMetadata(
            album_id=str(row.get(self.MB_ALBUM_ID_COLUMN)),
            artist_name=row.get("artist_name"),
            genres=parse_genres(row.get("genres")),
            first_release_year=parse_year(row.get("first_release_year")),
        )
