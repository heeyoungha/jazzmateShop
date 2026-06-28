import logging
from typing import Iterable

from app.clients.spring_callback_client import SpringCallbackClient
from app.core.config import settings
from app.core.error_codes import RecommendationErrorCode
from app.core.exceptions import EmbeddingError, RepositoryError
from app.repositories.album_embedding_repository import AlbumEmbeddingRepository
from app.repositories.album_metadata_repository import AlbumMetadataRepository
from app.repositories.user_listened_album_repository import UserListenedAlbumRepository
from app.repositories.user_taste_metadata_repository import UserTasteMetadataRepository
from app.schemas.recommendation import (
    AlbumCandidate,
    RecommendationCallbackItem,
    RecommendationReason,
    normalize_score,
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
        self.user_listened_album_repository = user_listened_album_repository
        self.user_taste_metadata_repository = user_taste_metadata_repository
        self.album_metadata_repository = album_metadata_repository
        self.taste_vector_service = taste_vector_service
        self.recommendation_rerank_service = recommendation_rerank_service
        self.top_k = top_k
        self.candidate_pool_size = candidate_pool_size

    async def recommend_by_review(self, review_id: int, review_content: str, user_id: str) -> None:
        
        # 감상문을 검색용 벡터로 변환한다
        try:
            embedding = await self.embedding_service.embed_review(review_content)
        except EmbeddingError:
            await self._send_failed_safely(
                review_id,
                RecommendationErrorCode.EMBEDDING_FAILED,
                "감상문 임베딩 생성에 실패했습니다.",
            )
            return
        
        try:
            reviewed_album_embeddings = self.user_listened_album_repository.find_by_user_id(
                user_id
            )
        except RepositoryError:
            await self._send_failed_safely(
                review_id,
                RecommendationErrorCode.SEARCH_FAILED,
                "사용자 감상 이력 조회에 실패했습니다.",
            )
            return

        # 감상 이력이 있으면 감상문 벡터와 취향 벡터를 블렌딩한다
        query_vector = embedding
        if reviewed_album_embeddings:
            query_vector = self.taste_vector_service.build_query_vector(
                embedding, reviewed_album_embeddings
            )

        # 검색 벡터로 유사 앨범 후보를 조회한다
        try:
            candidates = await self.album_embedding_repository.find_similar_albums(
                query_vector, self.candidate_pool_size
            )
        except RepositoryError:
            await self._send_failed_safely(
                review_id,
                RecommendationErrorCode.SEARCH_FAILED,
                "유사 앨범 검색에 실패했습니다.",
            )
            return

        if not candidates:
            await self._send_failed_safely(
                review_id,
                RecommendationErrorCode.NO_CANDIDATES,
                "추천 후보가 없습니다.",
            )
            return

        try:
            candidates = self._rerank_candidates(user_id, list(candidates))
        except RepositoryError:
            await self._send_failed_safely(
                review_id,
                RecommendationErrorCode.SEARCH_FAILED,
                "추천 메타데이터 조회에 실패했습니다.",
            )
            return

        # 후보 앨범별 추천 사유를 생성한다
        try:
            reasons = await self.recommendation_reason_service.generate_reasons(
                review_content, candidates
            )
        except Exception as exc:
            logger.exception("Recommendation reason generation failed: %s", exc)
            await self._send_failed_safely(
                review_id,
                RecommendationErrorCode.REASON_FAILED,
                "추천 사유 생성에 실패했습니다.",
            )
            return

        recommendations = self._build_callback_items(candidates, reasons)

        # 완료 결과는 Spring Boot 콜백 API로 전달한다
        try:
            await self.spring_callback_client.send_completed_result(
                review_id, recommendations
            )
        except Exception as exc:
            logger.exception("Spring callback failed: %s", exc)

    def _rerank_candidates(
        self, user_id: str, candidates: list[AlbumCandidate]
    ) -> list[AlbumCandidate]:
        if not candidates:
            return candidates

        user_metadata = self.user_taste_metadata_repository.find_by_user_id(user_id)
        candidate_metadata_by_album_id = (
            self.album_metadata_repository.find_by_album_reference_ids(
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
        try:
            await self.spring_callback_client.send_failed_result(
                review_id, error_code, message
            )
        except Exception as exc:
            logger.exception("Spring callback failed: %s", exc)
