from types import SimpleNamespace

import pytest

from app.api.dependencies import get_recommendation_service
from app.core.exceptions import ConfigurationError


class FakeDatabaseClient:
    pass


class FakeOpenAiClient:
    pass


class FakeHttpClient:
    pass


DEFAULT = object()
MISSING = object()


def make_request(
    database=DEFAULT,
    openai_embedding_client=DEFAULT,
    openai_chat_client=DEFAULT,
    spring_http_client=DEFAULT,
):
    state = SimpleNamespace()
    resources = {
        "database": FakeDatabaseClient() if database is DEFAULT else database,
        "openai_embedding_client": (
            FakeOpenAiClient()
            if openai_embedding_client is DEFAULT
            else openai_embedding_client
        ),
        "openai_chat_client": (
            FakeOpenAiClient() if openai_chat_client is DEFAULT else openai_chat_client
        ),
        "spring_http_client": (
            FakeHttpClient() if spring_http_client is DEFAULT else spring_http_client
        ),
    }
    for name, value in resources.items():
        if value is not MISSING:
            setattr(state, name, value)
    app = SimpleNamespace(state=state)
    return SimpleNamespace(app=app)


def test_get_recommendation_service_uses_app_state_resources():
    """dependency provider는 app.state 리소스를 협력 객체에 주입한다."""
    database = FakeDatabaseClient()
    embedding_client = FakeOpenAiClient()
    chat_client = FakeOpenAiClient()
    http_client = FakeHttpClient()
    request = make_request(
        database=database,
        openai_embedding_client=embedding_client,
        openai_chat_client=chat_client,
        spring_http_client=http_client,
    )

    service = get_recommendation_service(request)

    assert service.album_embedding_repository.database is database
    assert service.embedding_service.openai_client is embedding_client
    assert service.recommendation_reason_service.openai_client is chat_client
    assert service.spring_callback_client.http_client is http_client


@pytest.mark.parametrize(
    "resource_name",
    [
        "database",
        "openai_embedding_client",
        "openai_chat_client",
        "spring_http_client",
    ],
)
def test_get_recommendation_service_missing_resource_raises_configuration_error(
    resource_name,
):
    """필수 app.state 리소스가 없으면 설정 누락 예외가 발생한다."""
    request = make_request(**{resource_name: MISSING})

    with pytest.raises(ConfigurationError, match=f"app.state.{resource_name}"):
        get_recommendation_service(request)


@pytest.mark.parametrize(
    "resource_name",
    [
        "database",
        "openai_embedding_client",
        "openai_chat_client",
        "spring_http_client",
    ],
)
def test_get_recommendation_service_none_resource_raises_configuration_error(
    resource_name,
):
    """필수 app.state 리소스가 None이면 설정 누락 예외가 발생한다."""
    request = make_request(**{resource_name: None})

    with pytest.raises(ConfigurationError, match=f"app.state.{resource_name}"):
        get_recommendation_service(request)
