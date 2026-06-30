import importlib

import pytest

from app.core.config import settings
from app.core.exceptions import ConfigurationError, RepositoryError


def embedding(value: float) -> list[float]:
    return [value] * settings.EMBEDDING_DIMENSIONS


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def select(self, columns):
        self.calls.append(("select", columns))
        return self

    def eq(self, column, value):
        self.calls.append(("eq", column, value))
        return self

    @property
    def not_(self):
        self.calls.append(("not",))
        return self

    def is_(self, column, value):
        self.calls.append(("is", column, value))
        return self

    def execute(self):
        return type("Response", (), {"data": self.rows})()


class FakeDatabase:
    def __init__(self, rows=None):
        self.calls = []
        default_rows = [
            {"review_embedding": embedding(0.1)},
            {"review_embedding": embedding(0.3)},
        ]
        self.query = FakeQuery(rows if rows is not None else default_rows)

    def from_(self, table):
        self.calls.append(("from", table))
        return self.query


def repository_class():
    module = importlib.import_module(
        "app.repositories.user_review_embedding_repository"
    )
    return module.UserReviewEmbeddingRepository


def test_find_by_user_id_returns_review_embeddings():
    """user_id로 저장된 review_embedding 목록을 반환한다."""
    database = FakeDatabase()
    repository = repository_class()(database=database)

    result = repository.find_by_user_id("1")

    assert result == [embedding(0.1), embedding(0.3)]


def test_find_by_user_id_parses_string_embeddings():
    """DB가 vector를 문자열로 반환해도 float 리스트로 변환한다."""
    database = FakeDatabase(rows=[
        {"review_embedding": str(embedding(0.1))},
    ])
    repository = repository_class()(database=database)

    result = repository.find_by_user_id("1")

    assert result == [embedding(0.1)]


def test_find_by_user_id_returns_empty_list_when_no_embeddings():
    """저장된 review_embedding이 없으면 빈 리스트를 반환한다."""
    database = FakeDatabase(rows=[])
    repository = repository_class()(database=database)

    result = repository.find_by_user_id("1")

    assert result == []
    assert database.calls == [("from", "user_reviews")]


def test_find_by_user_id_invalid_embedding_raises_repository_error():
    """DB embedding 값이 깨져 있으면 RepositoryError로 변환한다."""
    database = FakeDatabase(rows=[
        {"review_embedding": {"invalid": "value"}},
    ])
    repository = repository_class()(database=database)

    with pytest.raises(RepositoryError):
        repository.find_by_user_id("1")


def test_find_by_user_id_invalid_embedding_dimensions_raises_repository_error():
    """DB embedding 차원이 설정과 다르면 RepositoryError로 변환한다."""
    database = FakeDatabase(rows=[
        {"review_embedding": [0.1, 0.2]},
    ])
    repository = repository_class()(database=database)

    with pytest.raises(RepositoryError):
        repository.find_by_user_id("1")


def test_user_review_embedding_repository_requires_database_client():
    """DB client 없이 Repository를 생성하면 설정 누락 예외가 발생한다."""
    with pytest.raises(ConfigurationError, match="database client"):
        repository_class()(database=None)
