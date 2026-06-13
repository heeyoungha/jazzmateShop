from typing import Iterable, Optional

from app.core.config import settings
from app.core.error_codes import RecommendationErrorCode
from app.core.exceptions import CallbackError, ConfigurationError
from app.schemas.recommendation import (
    RecommendationCallbackItem,
    RecommendationCallbackRequest,
)


class SpringCallbackClient:

    CALLBACK_PATH_TEMPLATE = "/api/user-reviews/{review_id}/recommendations"

    def __init__(
        self,
        base_url: Optional[str] = None,
        http_client=None,
    ):
        if http_client is None:
            raise ConfigurationError("SpringCallbackClient requires an http client.")
        self.base_url = (base_url or settings.SPRING_BASE_URL).rstrip("/")
        self.http_client = http_client

    async def send_completed_result(
        self, review_id: int, recommendations: Iterable[RecommendationCallbackItem]
    ) -> None:
        await self._post_callback(review_id, RecommendationCallbackRequest.completed(recommendations))

    async def send_failed_result(
        self, review_id: int, error_code: RecommendationErrorCode, message: str
    ) -> None:
        await self._post_callback(review_id, RecommendationCallbackRequest.failed(error_code, message))

    async def _post_callback(
        self, review_id: int, payload: RecommendationCallbackRequest
    ) -> None:

        url = f"{self.base_url}{self.CALLBACK_PATH_TEMPLATE.format(review_id=review_id)}"

        try:
            response = await self.http_client.post(url, json=payload.model_dump(by_alias=True, mode="json"))
            if not 200 <= response.status_code < 300:
                raise CallbackError(
                    f"Spring callback failed: status={response.status_code}, body={response.text}"
                )
        except CallbackError:
            raise
        except Exception as exc:
            raise CallbackError(str(exc)) from exc
