import logging
from typing import Any, Iterable
from app.schemas.recommendation import AlbumCandidate

from app.clients.spring_callback_client import SpringCallbackClient
from app.core.config import settings
from app.core.error_codes import RecommendationErrorCode
from app.core.exceptions import ConfigurationError, EmbeddingError, RepositoryError
from app.repositories.album_embedding_repository import AlbumEmbeddingRepository
from app.schemas.recommendation import (
    RecommendationCallbackItem,
    RecommendationReason,
    normalize_score,
)
from app.services.embedding_service import EmbeddingService
from app.services.recommendation_reason_service import RecommendationReasonService


logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        album_embedding_repository: AlbumEmbeddingRepository,
        recommendation_reason_service: RecommendationReasonService,
        spring_callback_client: SpringCallbackClient,
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
        self.top_k = top_k

    async def recommend_by_review(self, review_id: int, review_content: str) -> None:
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
            candidates = await self.album_embedding_repository.find_similar_albums(
                embedding, self.top_k
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

        reasons = await self.recommendation_reason_service.generate_reasons(
            review_content, candidates
        )
        recommendations = self._build_callback_items(candidates, reasons)

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
                recommendation_score=normalize_score(candidate.similarity),
                recommendation_reason=reason_by_album_id.get(candidate.album_id, ""),
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
