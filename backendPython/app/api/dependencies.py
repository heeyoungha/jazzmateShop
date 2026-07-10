from fastapi import Request

from app.core.exceptions import ConfigurationError
from app.clients.spring_callback_client import SpringCallbackClient
from app.repositories.album_embedding_repository import AlbumEmbeddingRepository
from app.repositories.album_metadata_repository import AlbumMetadataRepository
from app.repositories.user_listened_album_repository import UserListenedAlbumRepository
from app.repositories.user_review_embedding_repository import UserReviewEmbeddingRepository
from app.repositories.user_taste_metadata_repository import UserTasteMetadataRepository
from app.repositories.pg.album_embedding_repository import PgAlbumEmbeddingRepository
from app.repositories.pg.album_metadata_repository import PgAlbumMetadataRepository
from app.repositories.pg.user_listened_album_repository import PgUserListenedAlbumRepository
from app.repositories.pg.user_review_embedding_repository import PgUserReviewEmbeddingRepository
from app.repositories.pg.user_taste_metadata_repository import PgUserTasteMetadataRepository
from app.services.embedding_service import EmbeddingService
from app.services.recommendation_reason_service import RecommendationReasonService
from app.services.recommendation_service import RecommendationService
from app.services.recommendation_rerank_service import RecommendationRerankService
from app.services.taste_vector_service import TasteVectorService


def _get_required_app_state(request: Request, resource_name: str):
    value = getattr(request.app.state, resource_name, None)
    if value is None:
        raise ConfigurationError(
            f"FastAPI app.state.{resource_name} is not configured."
        )
    return value


def get_recommendation_service(request: Request) -> RecommendationService:
    embedding_client = _get_required_app_state(request, "openai_embedding_client")
    chat_client = _get_required_app_state(request, "openai_chat_client")
    spring_http_client = _get_required_app_state(request, "spring_http_client")

    pg_pool = getattr(request.app.state, "pg_pool", None)
    if pg_pool is not None:
        album_embedding_repo = PgAlbumEmbeddingRepository(pool=pg_pool)
        album_metadata_repo = PgAlbumMetadataRepository(pool=pg_pool)
        user_listened_repo = PgUserListenedAlbumRepository(pool=pg_pool)
        user_review_embedding_repo = PgUserReviewEmbeddingRepository(pool=pg_pool)
        user_taste_metadata_repo = PgUserTasteMetadataRepository(pool=pg_pool)
    else:
        database = _get_required_app_state(request, "database")
        album_embedding_repo = AlbumEmbeddingRepository(database=database)
        album_metadata_repo = AlbumMetadataRepository(database=database)
        user_listened_repo = UserListenedAlbumRepository(database=database)
        user_review_embedding_repo = UserReviewEmbeddingRepository(database=database)
        user_taste_metadata_repo = UserTasteMetadataRepository(database=database)

    return RecommendationService(
        embedding_service=EmbeddingService(openai_client=embedding_client),
        album_embedding_repository=album_embedding_repo,
        recommendation_reason_service=RecommendationReasonService(
            openai_client=chat_client
        ),
        spring_callback_client=SpringCallbackClient(http_client=spring_http_client),
        user_review_embedding_repository=user_review_embedding_repo,
        user_listened_album_repository=user_listened_repo,
        user_taste_metadata_repository=user_taste_metadata_repo,
        album_metadata_repository=album_metadata_repo,
        taste_vector_service=TasteVectorService(),
        recommendation_rerank_service=RecommendationRerankService(),
    )
