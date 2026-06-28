import logging
from typing import Any, Iterable
from app.schemas.recommendation import AlbumCandidate

from app.clients.spring_callback_client import SpringCallbackClient
from app.core.config import settings
from app.core.error_codes import RecommendationErrorCode
from app.core.exceptions import ConfigurationError, EmbeddingError, RepositoryError
from app.repositories.album_embedding_repository import AlbumEmbeddingRepository
from app.repositories.user_listened_album_repository import UserListenedAlbumRepository
from app.schemas.recommendation import (
    RecommendationCallbackItem,
    RecommendationReason,
    normalize_score,
)
from app.services.embedding_service import EmbeddingService
from app.services.recommendation_reason_service import RecommendationReasonService
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
        taste_vector_service: TasteVectorService,
        top_k: int = settings.RECOMMENDATION_TOP_K,
    ):
        if embedding_service is None:
            raise ConfigurationError(
                "RecommendationService requires an EmbeddingService."
            )
        self.embedding_service = embedding_service
        if album_embedding_repository is None:
            raise ConfigurationError(
                "RecommendationService requires an AlbumEmbeddingRepository."
            )
        self.album_embedding_repository = album_embedding_repository
        if recommendation_reason_service is None:
            raise ConfigurationError(
                "RecommendationService requires a RecommendationReasonService."
            )
        self.recommendation_reason_service = recommendation_reason_service
        if spring_callback_client is None:
            raise ConfigurationError(
                "RecommendationService requires a SpringCallbackClient."
            )
        self.spring_callback_client = spring_callback_client
        if user_listened_album_repository is None:
            raise ConfigurationError(
                "RecommendationService requires a UserListenedAlbumRepository."
            )
        self.user_listened_album_repository = user_listened_album_repository
        if taste_vector_service is None:
            raise ConfigurationError(
                "RecommendationService requires a TasteVectorService."
            )
        self.taste_vector_service = taste_vector_service
        self.top_k = top_k

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
        
        # 이전 감상 앨범의 임베딩을 조회한다
        reviewed_album_embeddings = self.user_listened_album_repository.find_by_user_id(
            user_id
        )

        # 감상 이력이 있으면 감상문 벡터와 취향 벡터를 블렌딩한다
        query_vector = embedding
        if reviewed_album_embeddings:
            query_vector = self.taste_vector_service.build_query_vector(
                embedding, reviewed_album_embeddings
            )

        # 검색 벡터로 유사 앨범 후보를 조회한다
        try:
            candidates = await self.album_embedding_repository.find_similar_albums(
                query_vector, self.top_k
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

        # 후보 앨범별 추천 사유를 생성한다
        reasons = await self.recommendation_reason_service.generate_reasons(
            review_content, candidates
        )
        recommendations = self._build_callback_items(candidates, reasons)

        # 완료 결과는 Spring Boot 콜백 API로 전달한다
        try:
            await self.spring_callback_client.send_completed_result(
                review_id, recommendations
            )
        except Exception as exc:
            logger.exception("Spring callback failed: %s", exc)

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
                album_artist=candidate.artist_name or None,
                album_title=candidate.album_title or None,
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
