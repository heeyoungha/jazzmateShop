import pytest

from app.core.error_codes import RecommendationErrorCode
from app.core.exceptions import EmbeddingError, RepositoryError
from app.schemas.recommendation import RecommendationReason
from app.services.recommendation_service import RecommendationService

from tests.fixtures import (
    ALBUM_ID_1,
    ALBUM_ID_2,
    REVIEW_CONTENT,
    REVIEW_ID,
    make_candidate,
)


class FakeEmbeddingService:
    def __init__(self, vector=None, error=None):
        self.vector = vector or [0.1] * 1536
        self.error = error
        self.calls = []

    async def embed_review(self, review_content):
        self.calls.append(review_content)
        if self.error:
            raise self.error
        return self.vector


class FakeAlbumEmbeddingRepository:
    def __init__(self, candidates=None, error=None):
        self.candidates = candidates if candidates is not None else [make_candidate()]
        self.error = error
        self.calls = []

    async def find_similar_albums(self, embedding, top_k):
        self.calls.append({"embedding": embedding, "top_k": top_k})
        if self.error:
            raise self.error
        return self.candidates


class FakeRecommendationReasonService:
    def __init__(self):
        self.calls = []

    async def generate_reasons(self, review_content, candidates):
        self.calls.append({"review_content": review_content, "candidates": candidates})
        return [
            RecommendationReason(
                album_id=candidate.album_id,
                recommendation_reason=f"{candidate.album_title} 추천 사유",
            )
            for candidate in candidates
        ]


class FakeSpringCallbackClient:
    def __init__(self, error=None):
        self.completed_calls = []
        self.failed_calls = []
        self.error = error

    async def send_completed_result(self, review_id, recommendations):
        self.completed_calls.append(
            {"review_id": review_id, "recommendations": recommendations}
        )
        if self.error:
            raise self.error

    async def send_failed_result(self, review_id, error_code, message):
        self.failed_calls.append(
            {"review_id": review_id, "error_code": error_code, "message": message}
        )
        if self.error:
            raise self.error


def build_service(
    embedding_service=None,
    repository=None,
    reason_service=None,
    callback_client=None,
    top_k=3,
):
    return RecommendationService(
        embedding_service=embedding_service or FakeEmbeddingService(),
        album_embedding_repository=repository or FakeAlbumEmbeddingRepository(),
        recommendation_reason_service=reason_service or FakeRecommendationReasonService(),
        spring_callback_client=callback_client or FakeSpringCallbackClient(),
        top_k=top_k,
    )


@pytest.mark.asyncio
async def test_recommend_by_review_success_sends_callback():
    """성공 경로는 임베딩 생성, TOP K 검색, 추천 사유 생성, COMPLETED 콜백까지 4단게가 모두 수행된다."""
    callback_client = FakeSpringCallbackClient()
    candidates = [
        make_candidate(ALBUM_ID_1, 0.95),
        make_candidate(ALBUM_ID_2, 0.91),
    ]
    service = build_service(
        repository=FakeAlbumEmbeddingRepository(candidates=candidates),
        callback_client=callback_client,
    )

    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT)

    assert callback_client.completed_calls[0]["review_id"] == REVIEW_ID
    assert len(callback_client.completed_calls[0]["recommendations"]) == 2
    assert callback_client.failed_calls == []


@pytest.mark.asyncio
async def test_recommend_by_review_normalizes_score_for_callback():
    """콜백 score는 0.0000~1.0000 범위로 정규화된다."""
    callback_client = FakeSpringCallbackClient()
    service = build_service(
        repository=FakeAlbumEmbeddingRepository(candidates=[make_candidate(similarity=1.4)]),
        callback_client=callback_client,
    )

    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT)

    score = callback_client.completed_calls[0]["recommendations"][0].recommendation_score
    assert 0 <= float(score) <= 1


@pytest.mark.asyncio
async def test_recommend_by_review_no_candidates_sends_failed_callback():
    """후보 0건이면 추천 사유 생성 없이 FAILED 콜백을 전송한다."""
    callback_client = FakeSpringCallbackClient()
    reason_service = FakeRecommendationReasonService()
    service = build_service(
        repository=FakeAlbumEmbeddingRepository(candidates=[]),
        reason_service=reason_service,
        callback_client=callback_client,
    )

    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT)

    assert callback_client.completed_calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.NO_CANDIDATES
    assert reason_service.calls == []


@pytest.mark.asyncio
async def test_recommend_by_review_embedding_failure_sends_failed_callback():
    """임베딩 실패 시 검색과 LLM을 호출하지 않고 FAILED 콜백을 전송한다."""
    callback_client = FakeSpringCallbackClient()
    repository = FakeAlbumEmbeddingRepository()
    reason_service = FakeRecommendationReasonService()
    service = build_service(
        embedding_service=FakeEmbeddingService(error=EmbeddingError("failed")),
        repository=repository,
        reason_service=reason_service,
        callback_client=callback_client,
    )

    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT)

    assert repository.calls == []
    assert reason_service.calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.EMBEDDING_FAILED


@pytest.mark.asyncio
async def test_recommend_by_review_search_failure_sends_failed_callback():
    """유사도 검색 실패 시 LLM을 호출하지 않고 FAILED 콜백을 전송한다."""
    callback_client = FakeSpringCallbackClient()
    reason_service = FakeRecommendationReasonService()
    service = build_service(
        repository=FakeAlbumEmbeddingRepository(error=RepositoryError("failed")),
        reason_service=reason_service,
        callback_client=callback_client,
    )

    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT)

    assert reason_service.calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.SEARCH_FAILED


@pytest.mark.asyncio
async def test_recommend_by_review_callback_failure_logs_and_raises(caplog):
    """콜백 전송 실패 시 로그를 남기고 예외를 전파한다."""
    service = build_service(
        callback_client=FakeSpringCallbackClient(error=RuntimeError("spring down"))
    )

    with pytest.raises(RuntimeError, match="spring down"):
        await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT)

    assert "spring down" in caplog.text
