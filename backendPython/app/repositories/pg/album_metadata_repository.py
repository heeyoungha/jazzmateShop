from app.core.exceptions import RepositoryError
from app.repositories.album_metadata_parsers import parse_genres, parse_year
from app.schemas.recommendation import AlbumMetadata


class PgAlbumMetadataRepository:
    def __init__(self, pool):
        self.pool = pool

    async def find_by_album_reference_ids(self, album_reference_ids: list[str]) -> dict[str, AlbumMetadata]:
        if not album_reference_ids:
            return {}
        sql = """
            SELECT
                ar.id::text                  AS reference_id,
                ma.gid::text                 AS album_id,
                ma.artist_name,
                array_to_json(ma.genres)::text AS genres,
                ma.first_release_year
            FROM album_reference ar
            JOIN mb_album ma ON ma.gid = ar.mb_release_group_id
            WHERE ar.id = ANY($1::uuid[])
              AND ar.mb_release_group_id IS NOT NULL
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql, album_reference_ids)
            return {
                row["reference_id"]: AlbumMetadata(
                    album_id=row["album_id"],
                    artist_name=row.get("artist_name"),
                    genres=parse_genres(row.get("genres")),
                    first_release_year=parse_year(row.get("first_release_year")),
                )
                for row in rows
            }
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc
