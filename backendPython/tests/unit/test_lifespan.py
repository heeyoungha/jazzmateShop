from fastapi.testclient import TestClient

from app import main as main_module


class FakeDatabaseClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeAsyncClient:
    def __init__(self):
        self.closed = False

    async def aclose(self):
        self.closed = True


def test_lifespan_registers_and_closes_app_scoped_resources(monkeypatch):
    """lifespan은 app-scoped 리소스를 app.state에 등록하고 종료 시 닫는다."""
    database = FakeDatabaseClient()
    embedding_client = FakeAsyncClient()
    chat_client = FakeAsyncClient()
    spring_http_client = FakeAsyncClient()

    monkeypatch.setattr(
        main_module,
        "create_database_client",
        lambda: database,
        raising=False,
    )
    monkeypatch.setattr(
        main_module,
        "create_openai_embedding_client",
        lambda: embedding_client,
        raising=False,
    )
    monkeypatch.setattr(
        main_module,
        "create_openai_chat_client",
        lambda: chat_client,
        raising=False,
    )
    monkeypatch.setattr(
        main_module,
        "create_spring_http_client",
        lambda: spring_http_client,
        raising=False,
    )

    with TestClient(main_module.app) as client:
        assert client.app.state.database is database
        assert client.app.state.openai_embedding_client is embedding_client
        assert client.app.state.openai_chat_client is chat_client
        assert client.app.state.spring_http_client is spring_http_client

    assert database.closed
    assert embedding_client.closed
    assert chat_client.closed
    assert spring_http_client.closed
