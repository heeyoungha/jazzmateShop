import importlib

import pytest
from pydantic import ValidationError


REQUIRED_ENV = {
    "SUPABASE_URL": "https://supabase.example.com",
    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
    "OPENAI_API_KEY": "test-openai-api-key",
    "OPENAI_EMBEDDING_MODEL": "text-embedding-3-small",
    "OPENAI_CHAT_MODEL": "gpt-4o-mini",
    "EMBEDDING_DIMENSIONS": "1536",
    "RECOMMENDATION_TOP_K": "3",
    "RECOMMENDATION_CANDIDATE_POOL_SIZE": "50",
    "SPRING_BASE_URL": "http://java-backend:8080",
    "OPENAI_TIMEOUT_SECONDS": "30",
    "OPENAI_MAX_RETRIES": "2",
}


def _set_required_env(monkeypatch, overrides=None):
    values = REQUIRED_ENV | (overrides or {})
    for name, value in values.items():
        monkeypatch.setenv(name, value)


@pytest.fixture(autouse=True)
def no_dotenv_file_loading(monkeypatch):
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: None)


@pytest.fixture(autouse=True)
def reload_config_after_test(monkeypatch):
    yield
    _set_required_env(monkeypatch)
    from app.core import config

    importlib.reload(config)


def test_settings_reads_environment_values(monkeypatch):
    """설정 값은 환경변수 또는 .env에서 주입된 값을 사용한다."""
    # given
    _set_required_env(
        monkeypatch,
        {
            "EMBEDDING_DIMENSIONS": "8",
            "RECOMMENDATION_TOP_K": "5",
            "RECOMMENDATION_CANDIDATE_POOL_SIZE": "20",
            "OPENAI_TIMEOUT_SECONDS": "12.5",
            "OPENAI_MAX_RETRIES": "4",
        },
    )

    # when
    from app.core import config

    reloaded = importlib.reload(config)

    # then
    assert reloaded.settings.OPENAI_EMBEDDING_MODEL == "text-embedding-3-small"
    assert reloaded.settings.OPENAI_CHAT_MODEL == "gpt-4o-mini"
    assert reloaded.settings.EMBEDDING_DIMENSIONS == 8
    assert reloaded.settings.RECOMMENDATION_TOP_K == 5
    assert reloaded.settings.RECOMMENDATION_CANDIDATE_POOL_SIZE == 20
    assert reloaded.settings.SPRING_BASE_URL == "http://java-backend:8080"
    assert reloaded.settings.OPENAI_TIMEOUT_SECONDS == 12.5
    assert reloaded.settings.OPENAI_MAX_RETRIES == 4


def test_settings_missing_required_environment_raises_configuration_error(monkeypatch):
    """필수 설정이 없으면 누락된 환경변수 이름으로 실패한다."""
    # given
    _set_required_env(monkeypatch)
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "")

    # when / then
    from app.core import config

    with pytest.raises(ValidationError, match="EMBEDDING_DIMENSIONS"):
        importlib.reload(config)


def test_settings_keeps_existing_defaults_for_optional_openai_settings(monkeypatch):
    """기존에 기본값이 있던 OpenAI 설정은 환경변수가 없어도 유지한다."""
    # given
    _set_required_env(monkeypatch)
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL")
    monkeypatch.delenv("OPENAI_MAX_RETRIES")

    # when
    from app.core import config

    reloaded = importlib.reload(config)

    # then
    assert reloaded.settings.OPENAI_EMBEDDING_MODEL == "text-embedding-3-small"
    assert reloaded.settings.OPENAI_MAX_RETRIES == 2
