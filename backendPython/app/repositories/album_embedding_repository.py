from typing import Any, List, Optional

from app.core.exceptions import ConfigurationError, RepositoryError
from app.schemas.recommendation import AlbumCandidate


class AlbumEmbeddingRepository:
    RPC_FUNC_NAME = "match_albums"

    def __init__(self, database: Optional[Any] = None):
        if database is None:
            raise ConfigurationError("AlbumEmbeddingRepository requires a database client.")
        self.database = database

    async def find_similar_albums(
        self, embedding: list[float], top_k: int
    ) -> List[AlbumCandidate]:
        try:
            response = await self.database.rpc(
                self.RPC_FUNC_NAME,
                {
                    "query_embedding": embedding,   # 사용자 감상문 벡터
                    "match_count": top_k,
                }
            ).execute()
            
            rows = list(response.data or [])

            sorted_rows = sorted(
                rows, key=lambda row: float(row.get("similarity", 0)), reverse=True
            )
            return [AlbumCandidate.from_row(row) for row in sorted_rows[:top_k]]
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc
