from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.exceptions import ConfigurationError, EmbeddingError
from app.services.embedding_service import EmbeddingService

from tests.fixtures import REVIEW_CONTENT


# OpenAI embeddings.create() 호출을 대체한다
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


# OpenAI 클라이언트를 대체한다
class FakeOpenAiClient:
    def __init__(self, embeddings):
        self.embeddings = embeddings


def test_embedding_service_requires_open_ai_client():
    """운영 조립 경로에서 OpenAI client 누락은 설정 오류로 실패한다."""
    # given / when / then
    with pytest.raises(ConfigurationError, match="openai client"):
        EmbeddingService(openai_client=None)


@pytest.mark.asyncio
async def test_embed_review_success_returns_1536_vector():
    """임베딩 성공 시 settings.EMBEDDING_DIMENSIONS 차원 벡터를 반환한다."""
    # given
    vector = [0.1] * settings.EMBEDDING_DIMENSIONS
    embeddings = FakeEmbeddings(
        response=SimpleNamespace(data=[SimpleNamespace(embedding=vector)])
    )
    service = EmbeddingService(openai_client=FakeOpenAiClient(embeddings))

    # when
    result = await service.embed_review(REVIEW_CONTENT)

    # then
    assert result == vector
    assert len(result) == settings.EMBEDDING_DIMENSIONS


@pytest.mark.asyncio
async def test_embed_review_open_ai_failure_raises_embedding_error():
    """OpenAI 임베딩 API 실패 시 EmbeddingError를 발생시킨다."""
    # given
    embeddings = FakeEmbeddings(error=RuntimeError("openai unavailable"))
    service = EmbeddingService(openai_client=FakeOpenAiClient(embeddings))

    # when / then
    with pytest.raises(EmbeddingError):
        await service.embed_review(REVIEW_CONTENT)


@pytest.mark.asyncio
async def test_embed_review_uses_configured_model():
    """설정된 OPENAI_EMBEDDING_MODEL과 review_content를 사용해 임베딩을 요청한다."""
    # given
    embeddings = FakeEmbeddings(
        response=SimpleNamespace(data=[SimpleNamespace(embedding=[0.1] * settings.EMBEDDING_DIMENSIONS)])
    )
    service = EmbeddingService(openai_client=FakeOpenAiClient(embeddings))

    # when
    await service.embed_review(REVIEW_CONTENT)

    # then
    assert embeddings.calls[0]["model"] == settings.OPENAI_EMBEDDING_MODEL
    assert embeddings.calls[0]["input"] == REVIEW_CONTENT
