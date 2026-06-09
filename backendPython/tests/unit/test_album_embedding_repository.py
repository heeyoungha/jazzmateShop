import pytest

from app.core.config import settings
from app.core.exceptions import RepositoryError
from app.repositories.album_embedding_repository import AlbumEmbeddingRepository


class FakeQuery:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.calls = []

    def from_(self, table_name):
        self.calls.append(("from", table_name))
        return self

    def select(self, columns):
        self.calls.append(("select", columns))
        return self

    def order(self, column_name, desc=False):
        self.calls.append(("order", column_name, desc))
        return self

    def limit(self, limit):
        self.calls.append(("limit", limit))
        return self

    def execute(self):
        if self.error:
            raise self.error
        return type("Response", (), {"data": self.rows})()


class FakeDatabaseClient:
    def __init__(self, query):
        self.query = query

    def from_(self, table_name):
        return self.query.from_(table_name)


@pytest.mark.asyncio
async def test_find_similar_albums_returns_top_k_by_similarity():
    """유사도 DESC 정렬 후 최대 K건을 반환한다."""
    rows = [
        {"album_id": "3", "similarity": 0.80},
        {"album_id": "1", "similarity": 0.98},
        {"album_id": "2", "similarity": 0.91},
    ]
    repository = AlbumEmbeddingRepository(database=FakeDatabaseClient(FakeQuery(rows)))

    result = await repository.find_similar_albums([0.1] * settings.EMBEDDING_DIMENSIONS, top_k=2)

    assert [candidate.album_id for candidate in result] == ["1", "2"]
    assert len(result) == 2


@pytest.mark.asyncio
async def test_find_similar_albums_queries_embedding_with_album_view():
    """조회 대상은 v_embedding_with_album으로 고정된다."""
    query = FakeQuery([])
    repository = AlbumEmbeddingRepository(database=FakeDatabaseClient(query))

    await repository.find_similar_albums([0.1] * settings.EMBEDDING_DIMENSIONS, top_k=3)

    assert ("from", "v_embedding_with_album") in query.calls


@pytest.mark.asyncio
async def test_find_similar_albums_no_rows_returns_empty_list():
    """후보가 없으면 빈 리스트를 반환한다."""
    repository = AlbumEmbeddingRepository(database=FakeDatabaseClient(FakeQuery([])))

    assert await repository.find_similar_albums([0.1] * settings.EMBEDDING_DIMENSIONS, top_k=3) == []


@pytest.mark.asyncio
async def test_find_similar_albums_db_failure_raises_repository_error():
    """DB 조회 실패 시 RepositoryError로 변환한다."""
    repository = AlbumEmbeddingRepository(
        database=FakeDatabaseClient(FakeQuery(error=RuntimeError("db down")))
    )

    with pytest.raises(RepositoryError):
        await repository.find_similar_albums([0.1] * settings.EMBEDDING_DIMENSIONS, top_k=3)
