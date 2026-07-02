from fastapi import APIRouter, BackgroundTasks, Depends, Response, status

from app.api.dependencies import get_recommendation_service
from app.schemas.recommendation import RecommendByReviewRequest
from app.services.recommendation_service import RecommendationService


router = APIRouter(prefix="/recommend", tags=["recommend"])


@router.post(
    "/review",
    status_code=status.HTTP_202_ACCEPTED,
    summary="AI 추천 요청",
    description="감상문 기반으로 유사 앨범을 비동기 추천합니다. 결과는 Spring Boot 콜백으로 전달됩니다.",
)
async def recommend_by_review(
    request: RecommendByReviewRequest,
    background_tasks: BackgroundTasks,
    service: RecommendationService = Depends(get_recommendation_service),
) -> Response:
    background_tasks.add_task(
        service.recommend_by_review,
        request.review_id,
        request.review_content,
        request.user_id,
    )
    return Response(status_code=status.HTTP_202_ACCEPTED)
