from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.exceptions import ConfigurationError, EmbeddingError
from app.services.embedding_service import EmbeddingService

from tests.fixtures import REVIEW_CONTENT


class FakeEmbeddings:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeOpenAiClient:
    def __init__(self, embeddings):
        self.embeddings = embeddings


def test_embedding_service_requires_open_ai_client():
    """운영 조립 경로에서 OpenAI client 누락은 설정 오류로 실패한다."""
    with pytest.raises(ConfigurationError, match="openai client"):
        EmbeddingService(openai_client=None)


@pytest.mark.asyncio
async def test_embed_review_success_returns_1536_vector():
    """임베딩 성공 시 settings.EMBEDDING_DIMENSIONS 차원 벡터를 반환한다."""
    vector = [0.1] * settings.EMBEDDING_DIMENSIONS
    embeddings = FakeEmbeddings(
        response=SimpleNamespace(data=[SimpleNamespace(embedding=vector)])
    )
    service = EmbeddingService(openai_client=FakeOpenAiClient(embeddings))

    result = await service.embed_review(REVIEW_CONTENT)

    assert result == vector
    assert len(result) == settings.EMBEDDING_DIMENSIONS


@pytest.mark.asyncio
async def test_embed_review_open_ai_failure_raises_embedding_error():
    """OpenAI 임베딩 API 실패 시 EmbeddingError를 발생시킨다."""
    embeddings = FakeEmbeddings(error=RuntimeError("openai unavailable"))
    service = EmbeddingService(openai_client=FakeOpenAiClient(embeddings))

    with pytest.raises(EmbeddingError):
        await service.embed_review(REVIEW_CONTENT)


@pytest.mark.asyncio
async def test_embed_review_uses_configured_model():
    """설정된 OPENAI_EMBEDDING_MODEL과 review_content를 사용해 임베딩을 요청한다."""
    embeddings = FakeEmbeddings(
        response=SimpleNamespace(data=[SimpleNamespace(embedding=[0.1] * settings.EMBEDDING_DIMENSIONS)])
    )
    service = EmbeddingService(openai_client=FakeOpenAiClient(embeddings))

    await service.embed_review(REVIEW_CONTENT)

    assert embeddings.calls[0]["model"] == settings.OPENAI_EMBEDDING_MODEL
    assert embeddings.calls[0]["input"] == REVIEW_CONTENT
