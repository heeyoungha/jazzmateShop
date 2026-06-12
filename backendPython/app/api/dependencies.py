from fastapi import Request

from app.core.exceptions import ConfigurationError
from app.clients.spring_callback_client import SpringCallbackClient
from app.repositories.album_embedding_repository import AlbumEmbeddingRepository
from app.services.embedding_service import EmbeddingService
from app.services.recommendation_reason_service import RecommendationReasonService
from app.services.recommendation_service import RecommendationService


def _get_required_app_state(request: Request, resource_name: str):
    value = getattr(request.app.state, resource_name, None)
    if value is None:
        raise ConfigurationError(
            f"FastAPI app.state.{resource_name} is not configured."
        )
    return value


def get_recommendation_service(request: Request) -> RecommendationService:
    database = _get_required_app_state(request, "database")
    embedding_client = _get_required_app_state(request, "openai_embedding_client")
    chat_client = _get_required_app_state(request, "openai_chat_client")
    spring_http_client = _get_required_app_state(request, "spring_http_client")

    return RecommendationService(
        embedding_service=EmbeddingService(openai_client=embedding_client),
        album_embedding_repository=AlbumEmbeddingRepository(database=database),
        recommendation_reason_service=RecommendationReasonService(
            openai_client=chat_client
        ),
        spring_callback_client=SpringCallbackClient(http_client=spring_http_client),
    )
