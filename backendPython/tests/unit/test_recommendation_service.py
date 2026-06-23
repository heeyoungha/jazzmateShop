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

USER_ID = "42"
REVIEW_EMBEDDING = [0.2, 0.4] + [0.0] * 1534  # 감상문 임베딩 (1536차원)
TASTE_VECTOR = [0.6, 0.8] + [0.0] * 1534  # 감상문 + 청취 이력 블렌딩 결과 벡터 (1536차원)

# OpenAI Embeddings API 호출을 대체한다
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


# Supabase 벡터 유사도 검색을 대체한다
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


# OpenAI Chat API로 추천 사유를 생성하는 LLM 호출을 대체한다
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


# Spring Boot로 추천 결과를 전송하는 HTTP 콜백을 대체한다
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


# 사용자가 이전에 감상한 앨범 임베딩을 DB에서 조회하는 레포지토리를 대체한다 (UserListenedAlbumRepository)
class FakeUserListenedAlbumRepository:
    def __init__(self, embeddings=None):
        self.embeddings = embeddings if embeddings is not None else []
        self.calls = []

    def find_by_user_id(self, user_id):
        self.calls.append(user_id)
        return self.embeddings


# 감상문 임베딩과 이전 감상 앨범 임베딩을 블렌딩해 검색 벡터를 만드는 서비스를 대체한다
class FakeTasteVectorService:
    def __init__(self, result_vector=None):
        self.result_vector = result_vector
        self.calls = []

    def build_query_vector(self, review_embedding, reviewed_album_embeddings):
        self.calls.append({
            "review_embedding": review_embedding,
            "reviewed_album_embeddings": reviewed_album_embeddings,
        })
        return self.result_vector if self.result_vector is not None else review_embedding


def build_service(
    embedding_service=None,
    repository=None,
    reason_service=None,
    callback_client=None,
    user_listened_album_repository=None,
    taste_vector_service=None,
    top_k=3,
):
    return RecommendationService(
        embedding_service=embedding_service or FakeEmbeddingService(),
        album_embedding_repository=repository or FakeAlbumEmbeddingRepository(),
        recommendation_reason_service=reason_service or FakeRecommendationReasonService(),
        spring_callback_client=callback_client or FakeSpringCallbackClient(),
        user_listened_album_repository=(
            user_listened_album_repository or FakeUserListenedAlbumRepository()
        ),
        taste_vector_service=taste_vector_service or FakeTasteVectorService(),
        top_k=top_k,
    )


@pytest.mark.asyncio
async def test_recommend_by_review_success_sends_callback():
    """성공 경로는 임베딩 생성, TOP K 검색, 추천 사유 생성, COMPLETED 콜백까지 4단게가 모두 수행된다."""
    # given
    callback_client = FakeSpringCallbackClient()
    candidates = [
        make_candidate(ALBUM_ID_1, 0.95),
        make_candidate(ALBUM_ID_2, 0.91),
    ]
    service = build_service(
        repository=FakeAlbumEmbeddingRepository(candidates=candidates),
        callback_client=callback_client,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert callback_client.completed_calls[0]["review_id"] == REVIEW_ID
    assert len(callback_client.completed_calls[0]["recommendations"]) == 2
    assert callback_client.failed_calls == []


@pytest.mark.asyncio
async def test_recommend_by_review_normalizes_score_for_callback():
    """콜백 score는 0.0000~1.0000 범위로 정규화된다."""
    # given
    callback_client = FakeSpringCallbackClient()
    service = build_service(
        repository=FakeAlbumEmbeddingRepository(candidates=[make_candidate(similarity=1.4)]),
        callback_client=callback_client,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    score = callback_client.completed_calls[0]["recommendations"][0].recommendation_score
    assert 0 <= float(score) <= 1


@pytest.mark.asyncio
async def test_recommend_by_review_no_candidates_sends_failed_callback():
    """후보 0건이면 추천 사유 생성 없이 FAILED 콜백을 전송한다."""
    # given
    callback_client = FakeSpringCallbackClient()
    reason_service = FakeRecommendationReasonService()
    service = build_service(
        repository=FakeAlbumEmbeddingRepository(candidates=[]),
        reason_service=reason_service,
        callback_client=callback_client,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert callback_client.completed_calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.NO_CANDIDATES
    assert reason_service.calls == []


@pytest.mark.asyncio
async def test_recommend_by_review_embedding_failure_sends_failed_callback():
    """임베딩 실패 시 검색과 LLM을 호출하지 않고 FAILED 콜백을 전송한다."""
    # given
    callback_client = FakeSpringCallbackClient()
    repository = FakeAlbumEmbeddingRepository()
    reason_service = FakeRecommendationReasonService()
    service = build_service(
        embedding_service=FakeEmbeddingService(error=EmbeddingError("failed")),
        repository=repository,
        reason_service=reason_service,
        callback_client=callback_client,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert repository.calls == []
    assert reason_service.calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.EMBEDDING_FAILED


@pytest.mark.asyncio
async def test_recommend_by_review_search_failure_sends_failed_callback():
    """유사도 검색 실패 시 LLM을 호출하지 않고 FAILED 콜백을 전송한다."""
    # given
    callback_client = FakeSpringCallbackClient()
    reason_service = FakeRecommendationReasonService()
    service = build_service(
        repository=FakeAlbumEmbeddingRepository(error=RepositoryError("failed")),
        reason_service=reason_service,
        callback_client=callback_client,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert reason_service.calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.SEARCH_FAILED


@pytest.mark.asyncio
async def test_recommend_by_review_callback_failure_logs_without_retry(caplog):
    """콜백 전송 실패 시 재시도 없이 로그만 남긴다."""
    # given
    callback_client = FakeSpringCallbackClient(error=RuntimeError("spring down"))
    service = build_service(
        callback_client=callback_client
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert "spring down" in caplog.text
    assert len(callback_client.completed_calls) == 1


@pytest.mark.asyncio
async def test_recommend_by_review_blends_review_and_taste_vector_when_user_has_matched_albums():
    """user_id가 있고 매칭 앨범이 있으면 TasteVectorService로 합산된 벡터로 검색한다."""
    # given
    album_repo = FakeAlbumEmbeddingRepository()
    user_listened_album_repository = FakeUserListenedAlbumRepository(
        embeddings=[TASTE_VECTOR]
    )
    taste_service = FakeTasteVectorService(result_vector=TASTE_VECTOR)

    service = build_service(
        embedding_service=FakeEmbeddingService(vector=REVIEW_EMBEDDING),
        repository=album_repo,
        user_listened_album_repository=user_listened_album_repository,
        taste_vector_service=taste_service,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert user_listened_album_repository.calls == [USER_ID]
    assert taste_service.calls[0]["review_embedding"] == REVIEW_EMBEDDING
    assert album_repo.calls[0]["embedding"] == TASTE_VECTOR


@pytest.mark.asyncio
async def test_recommend_by_review_falls_back_to_review_embedding_when_user_has_no_matched_albums():
    """user_id가 있어도 청취 이력이 없으면 review embedding 100%로 검색한다."""
    # given
    album_repo = FakeAlbumEmbeddingRepository()
    user_listened_album_repository = FakeUserListenedAlbumRepository(embeddings=[])
    taste_service = FakeTasteVectorService(result_vector=REVIEW_EMBEDDING)

    service = build_service(
        embedding_service=FakeEmbeddingService(vector=REVIEW_EMBEDDING),
        repository=album_repo,
        user_listened_album_repository=user_listened_album_repository,
        taste_vector_service=taste_service,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert taste_service.calls == []
    assert album_repo.calls[0]["embedding"] == REVIEW_EMBEDDING
