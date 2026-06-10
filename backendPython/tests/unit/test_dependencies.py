from types import SimpleNamespace

import pytest

from app.api.dependencies import get_recommendation_service
from app.core.exceptions import ConfigurationError


class FakeDatabaseClient:
    pass


def make_request(database=None, has_database=True):
    state = SimpleNamespace()
    if has_database:
        state.database = database
    app = SimpleNamespace(state=state)
    return SimpleNamespace(app=app)


def test_get_recommendation_service_uses_app_state_database():
    """dependency provider는 app.state.database를 Repository에 주입한다."""
    database = FakeDatabaseClient()
    request = make_request(database=database)

    service = get_recommendation_service(request)

    assert service.album_embedding_repository.database is database


def test_get_recommendation_service_missing_database_raises_configuration_error():
    """DB client가 없으면 NoneType 오류가 아니라 설정 누락 예외가 발생한다."""
    request = make_request(has_database=False)

    with pytest.raises(ConfigurationError, match="app.state.database"):
        get_recommendation_service(request)


def test_get_recommendation_service_none_database_raises_configuration_error():
    """app.state.database가 None이면 설정 누락 예외가 발생한다."""
    request = make_request(database=None)

    with pytest.raises(ConfigurationError, match="app.state.database"):
        get_recommendation_service(request)
