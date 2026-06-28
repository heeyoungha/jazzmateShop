import os

import pytest

# pytest collection 전에 실행 — settings = Settings() 가 import 시점에 실행되므로
# collection 이전에 필수 환경변수를 미리 설정해야 ValidationError가 나지 않는다.
# 실제 값은 사용하지 않으므로 테스트용 더미값으로 채운다.
_TEST_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "OPENAI_API_KEY": "test-openai-api-key",
    "OPENAI_CHAT_MODEL": "gpt-4o-mini",
    "EMBEDDING_DIMENSIONS": "1536",
    "RECOMMENDATION_TOP_K": "3",
    "RECOMMENDATION_CANDIDATE_POOL_SIZE": "50",
    "SPRING_BASE_URL": "http://java-backend:8080",
    "OPENAI_TIMEOUT_SECONDS": "30",
}


def pytest_configure(config):
    for key, value in _TEST_ENV.items():
        os.environ.setdefault(key, value)


class FakeDatabaseClient:
    def close(self):
        pass


class FakeAsyncClient:
    async def aclose(self):
        pass


@pytest.fixture
def client(monkeypatch):
    from fastapi.testclient import TestClient

    from app import main as main_module

    monkeypatch.setattr(
        main_module,
        "create_database_client",
        lambda: FakeDatabaseClient(),
        raising=False,
    )
    monkeypatch.setattr(
        main_module,
        "create_openai_embedding_client",
        lambda: FakeAsyncClient(),
        raising=False,
    )
    monkeypatch.setattr(
        main_module,
        "create_openai_chat_client",
        lambda: FakeAsyncClient(),
        raising=False,
    )
    monkeypatch.setattr(
        main_module,
        "create_spring_http_client",
        lambda: FakeAsyncClient(),
        raising=False,
    )

    main_module.app.dependency_overrides.clear()
    with TestClient(main_module.app) as test_client:
        yield test_client
    main_module.app.dependency_overrides.clear()
