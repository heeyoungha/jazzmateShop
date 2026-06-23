import importlib

import pytest

from app.core.config import settings
from app.core.exceptions import ConfigurationError, RepositoryError


def embedding(value: float) -> list[float]:
    return [value] * settings.EMBEDDING_DIMENSIONS


# Supabase Python 클라이언트의 메서드 체이닝을 대체한다
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

    def in_(self, column, values):
        self.calls.append(("in", column, values))
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


# Supabase DB 클라이언트를 대체한다
class FakeDatabase:
    def __init__(self):
        self.calls = []
        self.queries = {
            "user_reviews": FakeQuery([
                {"mb_album_gid": "album-1"},
                {"mb_album_gid": "album-2"},
                {"mb_album_gid": "album-1"},
            ]),
            "album_reference": FakeQuery([
                {"embedding": embedding(0.1)},
                {"embedding": embedding(0.3)},
            ]),
        }

    def from_(self, table):
        self.calls.append(("from", table))
        return self.queries[table]


def repository_class():
    module = importlib.import_module(
        "app.repositories.user_listened_album_repository"
    )
    return module.UserListenedAlbumRepository


def test_find_by_user_id_loads_distinct_reviewed_album_embeddings():
    """user_id로 조회한 앨범의 embedding을 중복 제거 후 반환한다."""
    # given
    database = FakeDatabase()
    repository = repository_class()(database=database)

    # when
    result = repository.find_by_user_id("1")

    # then
    assert result == [embedding(0.1), embedding(0.3)]


def test_find_by_user_id_parses_string_embeddings():
    """DB가 vector를 문자열로 반환해도 float 리스트로 변환한다."""
    # given
    database = FakeDatabase()
    database.queries["album_reference"] = FakeQuery([
        {"embedding": str(embedding(0.1))},
    ])
    repository = repository_class()(database=database)

    # when
    result = repository.find_by_user_id("1")

    # then
    assert result == [embedding(0.1)]


def test_find_by_user_id_returns_empty_list_when_all_reviews_have_no_mb_album_gid():
    """감상한 앨범이 있어도 mb_album_gid가 없으면 빈 리스트를 반환한다."""
    # given
    database = FakeDatabase()
    database.queries["user_reviews"] = FakeQuery([
        {"mb_album_gid": None},
        {"mb_album_gid": None},
    ])
    repository = repository_class()(database=database)

    # when
    result = repository.find_by_user_id("1")

    # then
    assert result == []


def test_find_by_user_id_returns_empty_list_when_user_has_no_matched_albums():
    """감상한 앨범이 없으면 빈 리스트를 반환한다."""
    # given
    database = FakeDatabase()
    database.queries["user_reviews"] = FakeQuery([])
    repository = repository_class()(database=database)

    # when
    result = repository.find_by_user_id("1")

    # then
    assert result == []
    assert database.calls == [("from", "user_reviews")]


def test_find_by_user_id_invalid_embedding_raises_repository_error():
    """DB embedding 값이 깨져 있으면 RepositoryError로 변환한다."""
    # given
    database = FakeDatabase()
    database.queries["album_reference"] = FakeQuery([
        {"embedding": {"invalid": "value"}},
    ])
    repository = repository_class()(database=database)

    # when / then
    with pytest.raises(RepositoryError):
        repository.find_by_user_id("1")


def test_find_by_user_id_invalid_embedding_dimensions_raises_repository_error():
    """DB embedding 차원이 설정과 다르면 RepositoryError로 변환한다."""
    # given
    database = FakeDatabase()
    database.queries["album_reference"] = FakeQuery([
        {"embedding": [0.1, 0.2]},
    ])
    repository = repository_class()(database=database)

    # when / then
    with pytest.raises(RepositoryError):
        repository.find_by_user_id("1")


def test_user_listened_album_repository_requires_database_client():
    """DB client 없이 Repository를 생성하면 설정 누락 예외가 발생한다."""
    # given / when / then
    with pytest.raises(ConfigurationError, match="database client"):
        repository_class()(database=None)
