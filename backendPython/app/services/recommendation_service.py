import asyncio
import logging
import time
from typing import Iterable

from app.clients.spring_callback_client import SpringCallbackClient
from app.core.config import settings
from app.core.error_codes import RecommendationErrorCode
from app.core.exceptions import EmbeddingError, RepositoryError
from app.repositories.album_embedding_repository import AlbumEmbeddingRepository
from app.repositories.album_metadata_repository import AlbumMetadataRepository
from app.repositories.user_listened_album_repository import UserListenedAlbumRepository
from app.repositories.user_review_embedding_repository import UserReviewEmbeddingRepository
from app.repositories.user_taste_metadata_repository import UserTasteMetadataRepository
from app.schemas.recommendation import (
    AlbumCandidate,
    RecommendationCallbackItem,
    RecommendationReason,
    normalize_score,
)
from app.observability.metrics import (
    dec_recommendation_in_flight,
    inc_recommendation_in_flight,
    observe_recommendation_stage,
    recommendation_stage_latency,
    record_recommendation_completed,
    record_recommendation_failed,
)
from app.services.embedding_service import EmbeddingService
from app.services.recommendation_reason_service import RecommendationReasonService
from app.services.recommendation_rerank_service import RecommendationRerankService
from app.services.taste_vector_service import TasteVectorService


logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        album_embedding_repository: AlbumEmbeddingRepository,
        recommendation_reason_service: RecommendationReasonService,
        spring_callback_client: SpringCallbackClient,
        user_review_embedding_repository: UserReviewEmbeddingRepository,
        user_listened_album_repository: UserListenedAlbumRepository,
        user_taste_metadata_repository: UserTasteMetadataRepository,
        album_metadata_repository: AlbumMetadataRepository,
        taste_vector_service: TasteVectorService,
        recommendation_rerank_service: RecommendationRerankService,
        top_k: int = settings.RECOMMENDATION_TOP_K,
        candidate_pool_size: int = settings.RECOMMENDATION_CANDIDATE_POOL_SIZE,
    ):
        self.embedding_service = embedding_service
        self.album_embedding_repository = album_embedding_repository
        self.recommendation_reason_service = recommendation_reason_service
        self.spring_callback_client = spring_callback_client
        self.user_review_embedding_repository = user_review_embedding_repository
        self.user_listened_album_repository = user_listened_album_repository
        self.user_taste_metadata_repository = user_taste_metadata_repository
        self.album_metadata_repository = album_metadata_repository
        self.taste_vector_service = taste_vector_service
        self.recommendation_rerank_service = recommendation_rerank_service
        self.top_k = top_k
        self.candidate_pool_size = candidate_pool_size

    async def recommend_by_review(self, review_id: int, review_content: str, user_id: str) -> None:
        t_start = time.monotonic()
        terminal_status = "unknown"
        inc_recommendation_in_flight()

        try:
            # 감상문을 검색용 벡터로 변환한다
            try:
                with observe_recommendation_stage("embedding"):
                    embedding = await self.embedding_service.embed_review(review_content)
                logger.debug("embedding done | review_id=%s | elapsed=%.3fs", review_id, time.monotonic() - t_start)
            except EmbeddingError:
                terminal_status = "failed_embedding"
                await self._send_failed_safely(
                    review_id,
                    RecommendationErrorCode.EMBEDDING_FAILED,
                    "감상문 임베딩 생성에 실패했습니다.",
                )
                return
            
            # personalization_lookup과 pgvector_search는 독립적이므로 병렬 실행
            # taste_vector 블렌딩을 위해 embedding 기반 query_vector를 먼저 준비
            query_vector = embedding

            async def _personalization_lookup():
                with observe_recommendation_stage("personalization_lookup"):
                    prev = await self.user_review_embedding_repository.find_by_user_id(user_id)
                    listened = await self.user_listened_album_repository.find_by_user_id(user_id)
                return prev, listened

            async def _pgvector_search():
                t_search = time.monotonic()
                with observe_recommendation_stage("pgvector_search"):
                    result = await self.album_embedding_repository.find_similar_albums(
                        query_vector, self.candidate_pool_size
                    )
                logger.debug("pgvector search done | review_id=%s | elapsed=%.3fs", review_id, time.monotonic() - t_search)
                return result

            try:
                (previous_review_embeddings, listened_album_embeddings), candidates = await asyncio.gather(
                    _personalization_lookup(),
                    _pgvector_search(),
                )
            except RepositoryError:
                terminal_status = "failed_search"
                await self._send_failed_safely(
                    review_id,
                    RecommendationErrorCode.SEARCH_FAILED,
                    "앨범 검색 또는 사용자 이력 조회에 실패했습니다.",
                )
                return

            # 감상 이력이 있으면 감상문 벡터와 취향 벡터를 블렌딩한다
            taste_embeddings = previous_review_embeddings + listened_album_embeddings
            if taste_embeddings:
                with observe_recommendation_stage("taste_vector"):
                    query_vector = self.taste_vector_service.build_query_vector(
                        embedding, taste_embeddings
                    )

            if not candidates:
                terminal_status = "failed_no_candidates"
                await self._send_failed_safely(
                    review_id,
                    RecommendationErrorCode.NO_CANDIDATES,
                    "추천 후보가 없습니다.",
                )
                return

            t_rerank = time.monotonic()
            try:
                with observe_recommendation_stage("rerank"):
                    candidates = await self._rerank_candidates(user_id, list(candidates))
                logger.debug("rerank done | review_id=%s | elapsed=%.3fs", review_id, time.monotonic() - t_rerank)
            except RepositoryError as exc:
                logger.exception("rerank RepositoryError: %s", exc)
                terminal_status = "failed_search"
                await self._send_failed_safely(
                    review_id,
                    RecommendationErrorCode.SEARCH_FAILED,
                    "추천 메타데이터 조회에 실패했습니다.",
                )
                return

            # 후보 앨범별 추천 사유를 생성한다
            t_reason = time.monotonic()
            try:
                with observe_recommendation_stage("reason_generation"):
                    reasons = await self.recommendation_reason_service.generate_reasons(
                        review_content, candidates
                    )
                logger.debug("reason generation done | review_id=%s | elapsed=%.3fs", review_id, time.monotonic() - t_reason)
            except Exception as exc:
                terminal_status = "failed_reason"
                logger.exception("Recommendation reason generation failed: %s", exc)
                await self._send_failed_safely(
                    review_id,
                    RecommendationErrorCode.REASON_FAILED,
                    "추천 사유 생성에 실패했습니다.",
                )
                return

            with observe_recommendation_stage("build_callback_payload"):
                recommendations = self._build_callback_items(candidates, reasons)

            # 완료 결과와 감상문 embedding을 Spring Boot 콜백 API로 전달한다.
            # embedding은 best-effort로 포함하며, Spring 측 저장 실패 시 추천 결과에 영향 없다.
            logger.debug("processing done, sending callback | review_id=%s | total_elapsed=%.3fs", review_id, time.monotonic() - t_start)
            try:
                with observe_recommendation_stage("spring_callback"):
                    await self.spring_callback_client.send_completed_result(
                        review_id, recommendations, embedding
                    )
                terminal_status = "completed"
                record_recommendation_completed()
                logger.debug("callback done | review_id=%s | total_elapsed=%.3fs", review_id, time.monotonic() - t_start)
            except Exception as exc:
                terminal_status = "callback_error"
                record_recommendation_failed("callback_error")
                logger.exception("Spring callback failed: %s", exc)
        finally:
            dec_recommendation_in_flight()
            recommendation_stage_latency.labels(
                stage="total",
                status=terminal_status,
            ).observe(time.monotonic() - t_start)

    async def _rerank_candidates(
        self, user_id: str, candidates: list[AlbumCandidate]
    ) -> list[AlbumCandidate]:
        if not candidates:
            return candidates

        user_metadata = await self.user_taste_metadata_repository.find_by_user_id(user_id)
        candidate_metadata_by_album_id = (
            await self.album_metadata_repository.find_by_album_reference_ids(
                [candidate.album_id for candidate in candidates]
            )
        )
        return self.recommendation_rerank_service.rerank(
            candidates,
            user_metadata,
            candidate_metadata_by_album_id,
            self.top_k,
        )

    def _build_callback_items(
        self, 
        candidates: Iterable[AlbumCandidate], 
        reasons: Iterable[RecommendationReason]
    ) -> list[RecommendationCallbackItem]:
        reason_by_album_id = {
            reason.album_id: reason.recommendation_reason
            for reason in reasons
        }
        return [
            RecommendationCallbackItem(
                album_id=candidate.album_id,
                album_artist=candidate.artist_name,
                album_title=candidate.album_title,
                recommendation_score=normalize_score(candidate.similarity),
                recommendation_reason=reason_by_album_id.get(candidate.album_id, ""),
                critics_review_id=candidate.critics_review_id,
            )
            for candidate in candidates
        ]

    async def _send_failed_safely(
        self, review_id: int, error_code: RecommendationErrorCode, message: str
    ) -> None:
        record_recommendation_failed(error_code.value)
        try:
            with observe_recommendation_stage("spring_callback"):
                await self.spring_callback_client.send_failed_result(
                    review_id, error_code, message
                )
        except Exception as exc:
            logger.exception("Spring callback failed: %s", exc)
