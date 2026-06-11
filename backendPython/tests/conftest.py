import pytest


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
