from app.core.exceptions import RepositoryError
from app.schemas.recommendation import AlbumCandidate


class PgAlbumEmbeddingRepository:
    def __init__(self, pool):
        self.pool = pool

    async def find_similar_albums(self, embedding: list[float], top_k: int) -> list[AlbumCandidate]:
        sql = """
            SELECT
                ar.id::text            AS album_id,
                ar.artist_name         AS album_artist,
                ar.album_title         AS album_title,
                ar.raw_id::text        AS critics_review_id,
                1 - (ar.embedding <=> $1::vector) AS similarity
            FROM album_reference ar
            WHERE ar.embedding IS NOT NULL
            ORDER BY ar.embedding <=> $1::vector
            LIMIT $2
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql, str(embedding), top_k)
            return sorted(
                [AlbumCandidate.from_row(dict(row)) for row in rows],
                key=lambda c: c.similarity,
                reverse=True,
            )
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc
