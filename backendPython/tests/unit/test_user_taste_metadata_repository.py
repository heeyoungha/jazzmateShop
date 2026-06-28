import pytest

from app.core.exceptions import ConfigurationError, RepositoryError
from app.repositories.user_taste_metadata_repository import UserTasteMetadataRepository

MB_ALBUM_GID_1 = "00000000-0000-0000-0000-000000001001"
MB_ALBUM_GID_2 = "00000000-0000-0000-0000-000000001002"


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


class FakeDatabase:
    def __init__(self):
        self.calls = []
        self.queries = {
            "user_reviews": FakeQuery([
                {"mb_album_gid": MB_ALBUM_GID_1},
                {"mb_album_gid": MB_ALBUM_GID_2},
                {"mb_album_gid": MB_ALBUM_GID_1},
            ]),
            "mb_album": FakeQuery([
                {
                    "gid": MB_ALBUM_GID_1,
                    "artist_name": "Miles Davis",
                    "genres": ["modal jazz", "hard bop"],
                    "first_release_year": 1959,
                },
                {
                    "gid": MB_ALBUM_GID_2,
                    "artist_name": "Wayne Shorter",
                    "genres": '["post-bop"]',
                    "first_release_year": "1966",
                },
            ]),
        }

    def from_(self, table):
        self.calls.append(("from", table))
        return self.queries[table]


@pytest.fixture
def database():
    return FakeDatabase()


@pytest.fixture
def repository(database):
    return UserTasteMetadataRepository(database=database)


def test_find_by_user_id_loads_distinct_mb_album_metadata(repository, database):
    """사용자 감상 이력의 mb_album_gid를 중복 제거해 mb_album 메타로 반환한다."""
    # when
    result = repository.find_by_user_id("1")

    # then
    assert [metadata.album_id for metadata in result] == [MB_ALBUM_GID_1, MB_ALBUM_GID_2]
    assert result[0].artist_name == "Miles Davis"
    assert result[0].genres == ("modal jazz", "hard bop")
    assert result[1].genres == ("post-bop",)
    assert result[1].first_release_year == 1966
    assert database.queries["mb_album"].calls[1] == ("in", "gid", [MB_ALBUM_GID_1, MB_ALBUM_GID_2])


def test_find_by_user_id_returns_empty_list_without_selected_albums(database):
    """선택된 MusicBrainz 앨범이 없으면 mb_album을 조회하지 않는다."""
    # given
    database.queries["user_reviews"] = FakeQuery([])
    repository = UserTasteMetadataRepository(database=database)

    # when
    result = repository.find_by_user_id("1")

    # then
    assert result == []
    assert database.calls == [("from", "user_reviews")]


def test_find_by_user_id_invalid_genres_raises_repository_error(database):
    """genres 응답 형식이 깨지면 RepositoryError로 변환한다."""
    # given
    database.queries["mb_album"] = FakeQuery([
        {
            "gid": MB_ALBUM_GID_1,
            "artist_name": "Miles Davis",
            "genres": {"invalid": "value"},
            "first_release_year": 1959,
        },
    ])
    repository = UserTasteMetadataRepository(database=database)

    # when / then
    with pytest.raises(RepositoryError):
        repository.find_by_user_id("1")


def test_user_taste_metadata_repository_requires_database_client():
    """DB client 없이 Repository를 생성하면 설정 누락 예외가 발생한다."""
    # given / when / then
    with pytest.raises(ConfigurationError, match="database client"):
        UserTasteMetadataRepository(database=None)
