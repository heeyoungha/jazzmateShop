from app.api.dependencies import get_recommendation_service
from app.main import app

from tests.fixtures import REVIEW_CONTENT, REVIEW_ID


def test_recommend_flow_missing_user_id_returns_422(client):
    """user_id가 누락된 요청은 422를 반환한다."""
    class FakeRecommendationService:
        async def recommend_by_review(self, *args):
            pass

    app.dependency_overrides[get_recommendation_service] = (
        lambda: FakeRecommendationService()
    )

    response = client.post(
        "/recommend/review",
        json={"review_id": REVIEW_ID, "review_content": REVIEW_CONTENT},
    )

    assert response.status_code == 422


def test_recommend_flow_passes_user_id_to_service(client):
    """user_id가 포함된 요청은 202를 반환하고 service에 값을 전달한다."""
    calls = []

    class FakeRecommendationService:
        async def recommend_by_review(self, review_id, review_content, user_id):
            calls.append(
                {
                    "review_id": review_id,
                    "review_content": review_content,
                    "user_id": user_id,
                }
            )

    app.dependency_overrides[get_recommendation_service] = (
        lambda: FakeRecommendationService()
    )

    response = client.post(
        "/recommend/review",
        json={
            "review_id": REVIEW_ID,
            "review_content": REVIEW_CONTENT,
            "user_id": "1",
        },
    )

    assert response.status_code == 202
    assert calls == [
        {
            "review_id": REVIEW_ID,
            "review_content": REVIEW_CONTENT,
            "user_id": "1",
        }
    ]
