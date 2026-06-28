import pytest

from app.core.exceptions import ConfigurationError, RepositoryError
from app.repositories.album_metadata_repository import AlbumMetadataRepository

ALBUM_REF_ID_1 = "00000000-0000-0000-0000-000000000101"
ALBUM_REF_ID_2 = "00000000-0000-0000-0000-000000000205"
MB_ALBUM_GID_1 = "00000000-0000-0000-0000-000000001001"
MB_ALBUM_GID_2 = "00000000-0000-0000-0000-000000001002"


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def select(self, columns):
        self.calls.append(("select", columns))
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
            "album_reference": FakeQuery([
                {"id": ALBUM_REF_ID_1, "mb_release_group_id": MB_ALBUM_GID_1},
                {"id": ALBUM_REF_ID_2, "mb_release_group_id": MB_ALBUM_GID_2},
            ]),
            "mb_album": FakeQuery([
                {
                    "gid": MB_ALBUM_GID_1,
                    "artist_name": "Miles Davis",
                    "genres": ["modal jazz"],
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
    return AlbumMetadataRepository(database=database)


def test_find_by_album_reference_ids_maps_candidate_ids_to_mb_metadata(repository):
    """album_reference.id 후보를 mb_release_group_id를 거쳐 mb_album 메타로 매핑한다."""
    # when
    result = repository.find_by_album_reference_ids([ALBUM_REF_ID_1, ALBUM_REF_ID_2])

    # then
    assert set(result.keys()) == {ALBUM_REF_ID_1, ALBUM_REF_ID_2}
    assert result[ALBUM_REF_ID_1].album_id == MB_ALBUM_GID_1
    assert result[ALBUM_REF_ID_1].artist_name == "Miles Davis"
    assert result[ALBUM_REF_ID_2].genres == ("post-bop",)
    assert result[ALBUM_REF_ID_2].first_release_year == 1966


def test_find_by_album_reference_ids_returns_empty_dict_without_ids(repository, database):
    """후보 id가 없으면 DB를 조회하지 않는다."""
    # when
    result = repository.find_by_album_reference_ids([])

    # then
    assert result == {}
    assert database.calls == []


def test_find_by_album_reference_ids_invalid_genres_raises_repository_error(database):
    """후보 메타 genres 응답 형식이 깨지면 RepositoryError로 변환한다."""
    # given
    database.queries["mb_album"] = FakeQuery([
        {
            "gid": MB_ALBUM_GID_1,
            "artist_name": "Miles Davis",
            "genres": {"invalid": "value"},
            "first_release_year": 1959,
        },
    ])
    repository = AlbumMetadataRepository(database=database)

    # when / then
    with pytest.raises(RepositoryError):
        repository.find_by_album_reference_ids([ALBUM_REF_ID_1])


def test_album_metadata_repository_requires_database_client():
    """DB client 없이 Repository를 생성하면 설정 누락 예외가 발생한다."""
    # given / when / then
    with pytest.raises(ConfigurationError, match="database client"):
        AlbumMetadataRepository(database=None)
