import pytest

from app.core.error_codes import RecommendationErrorCode
from app.core.exceptions import EmbeddingError, RepositoryError
from app.schemas.recommendation import AlbumMetadata, RecommendationReason
from app.services.recommendation_service import RecommendationService

from tests.fixtures import (
    ALBUM_ID_1,
    ALBUM_ID_2,
    REVIEW_CONTENT,
    REVIEW_ID,
    make_candidate,
)


# ---------------------------------------------------------------------------
# 테스트 공통 데이터
# ---------------------------------------------------------------------------

USER_ID = "42"
ALBUM_ID_3 = "album-3"
CANDIDATE_POOL_SIZE = 50
REVIEW_EMBEDDING = [0.2, 0.4] + [0.0] * 1534  # 감상문 임베딩 (1536차원)
TASTE_VECTOR = [0.6, 0.8] + [0.0] * 1534  # 감상문 + 청취 이력 블렌딩 결과 벡터 (1536차원)


# ---------------------------------------------------------------------------
# Fake 의존성: 외부 API 호출 대체
# ---------------------------------------------------------------------------

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


# OpenAI Chat API로 추천 사유를 생성하는 LLM 호출을 대체한다
class FakeRecommendationReasonService:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    async def generate_reasons(self, review_content, candidates):
        self.calls.append({"review_content": review_content, "candidates": candidates})
        if self.error:
            raise self.error
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


# ---------------------------------------------------------------------------
# Fake 의존성: DB repository 대체
# ---------------------------------------------------------------------------

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


# 사용자가 이전에 감상한 앨범 임베딩을 DB에서 조회하는 레포지토리를 대체한다 (UserListenedAlbumRepository)
class FakeUserListenedAlbumRepository:
    def __init__(self, embeddings=None, error=None):
        self.embeddings = embeddings if embeddings is not None else []
        self.error = error
        self.calls = []

    def find_by_user_id(self, user_id):
        self.calls.append(user_id)
        if self.error:
            raise self.error
        return self.embeddings


# 사용자가 이전에 감상한 앨범의 장르/아티스트/연도 메타데이터 조회를 대체한다
class FakeUserTasteMetadataRepository:
    def __init__(self, metadata=None, error=None):
        self.metadata = metadata if metadata is not None else []
        self.error = error
        self.calls = []

    def find_by_user_id(self, user_id):
        self.calls.append(user_id)
        if self.error:
            raise self.error
        return self.metadata


# 후보 앨범의 장르/아티스트/연도 메타데이터 조회를 대체한다
class FakeAlbumMetadataRepository:
    def __init__(self, metadata_by_album_id=None, error=None):
        self.metadata_by_album_id = (
            metadata_by_album_id if metadata_by_album_id is not None else {}
        )
        self.error = error
        self.calls = []

    def find_by_album_reference_ids(self, album_reference_ids):
        self.calls.append(album_reference_ids)
        if self.error:
            raise self.error
        return self.metadata_by_album_id


# ---------------------------------------------------------------------------
# Fake 의존성: 도메인 서비스 대체
# ---------------------------------------------------------------------------

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


# 후보 풀을 사용자 취향 메타데이터 기준으로 재정렬하는 서비스를 대체한다
class FakeRecommendationRerankService:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def rerank(self, candidates, user_metadata, candidate_metadata_by_album_id, top_k):
        self.calls.append({
            "candidates": candidates,
            "user_metadata": user_metadata,
            "candidate_metadata_by_album_id": candidate_metadata_by_album_id,
            "top_k": top_k,
        })
        return self.result if self.result is not None else candidates[:top_k]


# ---------------------------------------------------------------------------
# 테스트 대상 생성 헬퍼
# ---------------------------------------------------------------------------

# 각 테스트는 필요한 fake만 주입하고, 나머지는 기본 fake로 채워 RecommendationService를 만든다
def build_service(
    embedding_service=None,
    album_embedding_repository=None,
    reason_service=None,
    callback_client=None,
    user_listened_album_repository=None,
    user_taste_metadata_repository=None,
    album_metadata_repository=None,
    taste_vector_service=None,
    recommendation_rerank_service=None,
    top_k=3,
    candidate_pool_size=CANDIDATE_POOL_SIZE,
):
    return RecommendationService(
        embedding_service=embedding_service or FakeEmbeddingService(),
        album_embedding_repository=(
            album_embedding_repository or FakeAlbumEmbeddingRepository()
        ),
        recommendation_reason_service=reason_service or FakeRecommendationReasonService(),
        spring_callback_client=callback_client or FakeSpringCallbackClient(),
        user_listened_album_repository=(
            user_listened_album_repository or FakeUserListenedAlbumRepository()
        ),
        user_taste_metadata_repository=(
            user_taste_metadata_repository or FakeUserTasteMetadataRepository()
        ),
        album_metadata_repository=(
            album_metadata_repository or FakeAlbumMetadataRepository()
        ),
        taste_vector_service=taste_vector_service or FakeTasteVectorService(),
        recommendation_rerank_service=(
            recommendation_rerank_service or FakeRecommendationRerankService()
        ),
        top_k=top_k,
        candidate_pool_size=candidate_pool_size,
    )


# ---------------------------------------------------------------------------
# 성공 경로와 callback payload 검증
# ---------------------------------------------------------------------------

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
        album_embedding_repository=FakeAlbumEmbeddingRepository(candidates=candidates),
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
        album_embedding_repository=FakeAlbumEmbeddingRepository(
            candidates=[make_candidate(similarity=1.4)]
        ),
        callback_client=callback_client,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    score = callback_client.completed_calls[0]["recommendations"][0].recommendation_score
    assert 0 <= float(score) <= 1


# ---------------------------------------------------------------------------
# 실패 경로 검증
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recommend_by_review_no_candidates_sends_failed_callback():
    """후보 0건이면 추천 사유 생성 없이 FAILED 콜백을 전송한다."""
    # given
    callback_client = FakeSpringCallbackClient()
    reason_service = FakeRecommendationReasonService()
    service = build_service(
        album_embedding_repository=FakeAlbumEmbeddingRepository(candidates=[]),
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
    album_embedding_repository = FakeAlbumEmbeddingRepository()
    reason_service = FakeRecommendationReasonService()
    service = build_service(
        embedding_service=FakeEmbeddingService(error=EmbeddingError("failed")),
        album_embedding_repository=album_embedding_repository,
        reason_service=reason_service,
        callback_client=callback_client,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert album_embedding_repository.calls == []
    assert reason_service.calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.EMBEDDING_FAILED


@pytest.mark.asyncio
async def test_recommend_by_review_search_failure_sends_failed_callback():
    """유사도 검색 실패 시 LLM을 호출하지 않고 FAILED 콜백을 전송한다."""
    # given
    callback_client = FakeSpringCallbackClient()
    reason_service = FakeRecommendationReasonService()
    service = build_service(
        album_embedding_repository=FakeAlbumEmbeddingRepository(
            error=RepositoryError("failed")
        ),
        reason_service=reason_service,
        callback_client=callback_client,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert reason_service.calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.SEARCH_FAILED


@pytest.mark.asyncio
async def test_recommend_by_review_reason_generation_failure_sends_failed_callback(caplog):
    """추천 사유 생성 실패 시 완료 콜백을 보내지 않고 FAILED 콜백을 전송한다."""
    # given
    callback_client = FakeSpringCallbackClient()
    reason_service = FakeRecommendationReasonService(error=RuntimeError("llm failed"))
    service = build_service(
        reason_service=reason_service,
        callback_client=callback_client,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert "llm failed" in caplog.text
    assert callback_client.completed_calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.REASON_FAILED
    assert callback_client.failed_calls[0]["message"] == "추천 사유 생성에 실패했습니다."


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


# ---------------------------------------------------------------------------
# 사용자 감상 이력 기반 taste vector 검증
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recommend_by_review_blends_review_and_taste_vector_when_user_has_matched_albums():
    """user_id가 있고 매칭 앨범이 있으면 TasteVectorService로 합산된 벡터로 검색한다."""
    # given
    album_embedding_repository = FakeAlbumEmbeddingRepository()
    user_listened_album_repository = FakeUserListenedAlbumRepository(
        embeddings=[TASTE_VECTOR]
    )
    taste_service = FakeTasteVectorService(result_vector=TASTE_VECTOR)

    service = build_service(
        embedding_service=FakeEmbeddingService(vector=REVIEW_EMBEDDING),
        album_embedding_repository=album_embedding_repository,
        user_listened_album_repository=user_listened_album_repository,
        taste_vector_service=taste_service,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert user_listened_album_repository.calls == [USER_ID]
    assert taste_service.calls[0]["review_embedding"] == REVIEW_EMBEDDING
    assert album_embedding_repository.calls[0]["embedding"] == TASTE_VECTOR


@pytest.mark.asyncio
async def test_recommend_by_review_falls_back_to_review_embedding_when_user_has_no_matched_albums():
    """user_id가 있어도 청취 이력이 없으면 review embedding 100%로 검색한다."""
    # given
    album_embedding_repository = FakeAlbumEmbeddingRepository()
    user_listened_album_repository = FakeUserListenedAlbumRepository(embeddings=[])
    taste_service = FakeTasteVectorService(result_vector=REVIEW_EMBEDDING)

    service = build_service(
        embedding_service=FakeEmbeddingService(vector=REVIEW_EMBEDDING),
        album_embedding_repository=album_embedding_repository,
        user_listened_album_repository=user_listened_album_repository,
        taste_vector_service=taste_service,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert taste_service.calls == []
    assert album_embedding_repository.calls[0]["embedding"] == REVIEW_EMBEDDING


# ---------------------------------------------------------------------------
# 메타데이터 기반 rerank 검증
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recommend_by_review_fetches_candidate_pool_and_reranks_to_top_k():
    """추천 후보는 top 50까지 조회한 뒤 메타 기반 재순위로 최종 top_k만 콜백한다."""
    # given
    callback_client = FakeSpringCallbackClient()
    # top_k=2보다 많은 후보를 준비해, 최종 추천 개수와 rerank 후보 풀이 분리되는지 검증한다.
    candidates = [
        make_candidate(ALBUM_ID_1, 0.91),
        make_candidate(ALBUM_ID_2, 0.90),
        make_candidate(ALBUM_ID_3, 0.89),
    ]
    album_embedding_repository = FakeAlbumEmbeddingRepository(candidates=candidates)
    # fake repository가 user_id 조회 결과로 반환할 사용자 취향 메타데이터를 미리 정한다.
    user_metadata = [
        AlbumMetadata(
            album_id=ALBUM_ID_1,
            artist_name="Miles Davis",
            genres=["modal jazz"],
            first_release_year=1959,
        )
    ]
    user_metadata_repository = FakeUserTasteMetadataRepository(metadata=user_metadata)
    # fake repository가 후보 앨범 id 조회 결과로 반환할 앨범 메타데이터를 미리 정한다.
    candidate_metadata_by_album_id = {
        ALBUM_ID_2: AlbumMetadata(
            album_id=ALBUM_ID_2,
            artist_name="Wayne Shorter",
            genres=["post-bop"],
            first_release_year=1966,
        )
    }
    album_metadata_repository = FakeAlbumMetadataRepository(
        metadata_by_album_id=candidate_metadata_by_album_id
    )
    # 원래 유사도 순서와 다른 결과를 반환해, callback 순서가 rerank 결과를 따르는지 확인한다.
    reranked_candidates = [candidates[1], candidates[0]]
    rerank_service = FakeRecommendationRerankService(result=reranked_candidates)
    service = build_service(
        album_embedding_repository=album_embedding_repository,
        callback_client=callback_client,
        user_taste_metadata_repository=user_metadata_repository,
        album_metadata_repository=album_metadata_repository,
        recommendation_rerank_service=rerank_service,
        top_k=2,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    # 최종 top_k=2여도 벡터 검색은 설정된 rerank용 후보 풀을 넓게 가져온다.
    assert album_embedding_repository.calls[0]["top_k"] == CANDIDATE_POOL_SIZE
    # rerank에 필요한 사용자/후보 메타데이터 조회가 수행된다.
    assert user_metadata_repository.calls == [USER_ID]
    assert album_metadata_repository.calls == [[ALBUM_ID_1, ALBUM_ID_2, ALBUM_ID_3]]
    # rerank 서비스에는 최종 추천 개수 top_k가 함께 전달된다.
    assert rerank_service.calls[0]["top_k"] == 2
    # repository에서 조회된 메타데이터가 rerank 서비스 입력으로 그대로 전달된다.
    assert rerank_service.calls[0]["user_metadata"] == user_metadata
    assert (
        rerank_service.calls[0]["candidate_metadata_by_album_id"]
        == candidate_metadata_by_album_id
    )
    recommendations = callback_client.completed_calls[0]["recommendations"]
    # 최종 callback은 원래 유사도 순서가 아니라 rerank 결과 순서를 따른다.
    assert [item.album_id for item in recommendations] == [ALBUM_ID_2, ALBUM_ID_1]


@pytest.mark.asyncio
async def test_recommend_by_review_metadata_failure_sends_failed_callback():
    """메타 조회 실패는 FAILED 콜백으로 처리한다."""
    # given
    callback_client = FakeSpringCallbackClient()
    reason_service = FakeRecommendationReasonService()
    candidates = [
        make_candidate(ALBUM_ID_1, 0.91),
        make_candidate(ALBUM_ID_2, 0.90),
    ]
    rerank_service = FakeRecommendationRerankService()
    service = build_service(
        album_embedding_repository=FakeAlbumEmbeddingRepository(candidates=candidates),
        reason_service=reason_service,
        callback_client=callback_client,
        user_taste_metadata_repository=FakeUserTasteMetadataRepository(
            error=RepositoryError("metadata down")
        ),
        recommendation_rerank_service=rerank_service,
        top_k=1,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert callback_client.completed_calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.SEARCH_FAILED
    assert callback_client.failed_calls[0]["message"] == "추천 메타데이터 조회에 실패했습니다."
    assert rerank_service.calls == []
    assert reason_service.calls == []


@pytest.mark.asyncio
async def test_recommend_by_review_embedding_history_failure_sends_failed_callback():
    """사용자 감상 이력 조회 실패는 FAILED 콜백으로 처리한다."""
    # given
    album_embedding_repository = FakeAlbumEmbeddingRepository()
    taste_service = FakeTasteVectorService(result_vector=TASTE_VECTOR)
    callback_client = FakeSpringCallbackClient()
    service = build_service(
        embedding_service=FakeEmbeddingService(vector=REVIEW_EMBEDDING),
        album_embedding_repository=album_embedding_repository,
        callback_client=callback_client,
        user_listened_album_repository=FakeUserListenedAlbumRepository(
            error=RepositoryError("history down")
        ),
        taste_vector_service=taste_service,
    )

    # when
    await service.recommend_by_review(REVIEW_ID, REVIEW_CONTENT, user_id=USER_ID)

    # then
    assert callback_client.completed_calls == []
    assert callback_client.failed_calls[0]["error_code"] == RecommendationErrorCode.SEARCH_FAILED
    assert callback_client.failed_calls[0]["message"] == "사용자 감상 이력 조회에 실패했습니다."
    assert taste_service.calls == []
    assert album_embedding_repository.calls == []
