import pytest


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
