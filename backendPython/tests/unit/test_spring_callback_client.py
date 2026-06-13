import json
from decimal import Decimal

import httpx
import pytest

from app.core.error_codes import RecommendationErrorCode
from app.core.exceptions import CallbackError, ConfigurationError
from app.clients.spring_callback_client import SpringCallbackClient
from app.schemas.recommendation import RecommendationCallbackItem

from tests.fixtures import ALBUM_ID_1, CRITICS_REVIEW_ID_1, REVIEW_ID


def make_item():
    return RecommendationCallbackItem(
        album_id=ALBUM_ID_1,
        recommendation_score=Decimal("0.9423"),
        recommendation_reason="차분한 모달 재즈 분위기가 잘 맞습니다.",
        critics_review_id=CRITICS_REVIEW_ID_1,
    )


def test_spring_callback_client_requires_http_client():
    """운영 조립 경로에서 HTTP client 누락은 설정 오류로 실패한다."""
    with pytest.raises(ConfigurationError, match="http client"):
        SpringCallbackClient(
            base_url="https://spring.example.com",
            http_client=None,
        )


@pytest.mark.asyncio
async def test_send_completed_result_posts_expected_payload():
    """올바른 URL과 status=COMPLETED payload로 POST한다."""
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = SpringCallbackClient(
            base_url="https://spring.example.com",
            http_client=http_client,
        )

        await client.send_completed_result(REVIEW_ID, [make_item()])

    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == (
        f"https://spring.example.com/api/user-reviews/{REVIEW_ID}/recommendations"
    )
    payload = json.loads(request.content)
    assert payload["status"] == "COMPLETED"
    assert payload["recommendations"][0]["albumId"] == ALBUM_ID_1
    assert payload["recommendations"][0]["recommendationScore"] == "0.9423"
    assert payload["recommendations"][0]["recommendationReason"]
    assert payload["recommendations"][0]["criticsReviewId"] == CRITICS_REVIEW_ID_1


@pytest.mark.asyncio
async def test_send_failed_result_posts_expected_payload():
    """올바른 URL과 status=FAILED payload로 POST한다."""
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = SpringCallbackClient(
            base_url="https://spring.example.com",
            http_client=http_client,
        )

        await client.send_failed_result(
            REVIEW_ID,
            error_code=RecommendationErrorCode.NO_CANDIDATES,
            message="추천 후보가 없습니다.",
        )

    payload = json.loads(requests[0].content)
    assert payload == {
        "status": "FAILED",
        "recommendations": [],
        "errorCode": RecommendationErrorCode.NO_CANDIDATES,
        "message": "추천 후보가 없습니다.",
    }


@pytest.mark.asyncio
async def test_send_recommendations_empty_spring_response_body_200_success():
    """Spring이 200 OK + 빈 body를 반환하면 성공으로 처리한다."""
    async def handler(request):
        return httpx.Response(200, content=b"")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = SpringCallbackClient(
            base_url="https://spring.example.com",
            http_client=http_client,
        )

        await client.send_completed_result(REVIEW_ID, [make_item()])


@pytest.mark.asyncio
async def test_send_recommendations_non_2xx_raises_callback_error():
    """4xx/5xx 응답 시 CallbackError를 발생시킨다."""
    async def handler(request):
        return httpx.Response(500, content=b"error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = SpringCallbackClient(
            base_url="https://spring.example.com",
            http_client=http_client,
        )

        with pytest.raises(CallbackError):
            await client.send_completed_result(REVIEW_ID, [make_item()])


@pytest.mark.asyncio
async def test_send_recommendations_timeout_raises_callback_error():
    """타임아웃 시 CallbackError를 발생시킨다."""
    async def handler(request):
        raise httpx.TimeoutException("timeout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = SpringCallbackClient(
            base_url="https://spring.example.com",
            http_client=http_client,
        )

        with pytest.raises(CallbackError):
            await client.send_completed_result(REVIEW_ID, [make_item()])
