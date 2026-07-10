from app.core.exceptions import RepositoryError
from app.repositories.album_metadata_parsers import parse_genres, parse_year
from app.schemas.recommendation import AlbumMetadata


class PgUserTasteMetadataRepository:
    def __init__(self, pool):
        self.pool = pool

    async def find_by_user_id(self, user_id: str) -> list[AlbumMetadata]:
        sql = """
            SELECT DISTINCT ON (ma.gid)
                ma.gid::text          AS album_id,
                ma.artist_name,
                ma.genres::text       AS genres,
                ma.first_release_year
            FROM user_reviews ur
            JOIN mb_album ma ON ma.gid = ur.mb_album_gid
            WHERE ur.user_id = $1
              AND ur.mb_album_gid IS NOT NULL
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql, user_id)
            return [self._parse(dict(row)) for row in rows]
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc

    def _parse(self, row: dict) -> AlbumMetadata:
        return AlbumMetadata(
            album_id=row["album_id"],
            artist_name=row.get("artist_name"),
            genres=parse_genres(row.get("genres")),
            first_release_year=parse_year(row.get("first_release_year")),
        )
