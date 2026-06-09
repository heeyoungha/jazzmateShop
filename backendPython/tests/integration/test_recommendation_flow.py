import pytest

from app.services.recommendation_service import RecommendationService

from tests.fixtures import REVIEW_CONTENT, REVIEW_ID


def test_recommend_flow_valid_request_returns_202_and_processes_callback(
    client, monkeypatch
):
    """유효한 추천 요청 수신 시 202를 반환하고 RecommendationService에 처리를 위임한다."""
    calls = []

    async def spy(self, review_id, review_content):
        calls.append({"review_id": review_id, "review_content": review_content})

    monkeypatch.setattr(RecommendationService, "recommend_by_review", spy)

    response = client.post(
        "/recommend/review",
        json={"review_id": REVIEW_ID, "review_content": REVIEW_CONTENT},
    )

    assert response.status_code == 202
    assert calls == [{"review_id": REVIEW_ID, "review_content": REVIEW_CONTENT}]

