from fastapi import APIRouter, BackgroundTasks, Depends, Response, status

from app.api.dependencies import get_recommendation_service
from app.schemas.recommendation import RecommendByReviewRequest
from app.services.recommendation_service import RecommendationService


router = APIRouter(prefix="/recommend")


@router.post("/review", status_code=status.HTTP_202_ACCEPTED)
async def recommend_by_review(
    request: RecommendByReviewRequest,
    background_tasks: BackgroundTasks,
    service: RecommendationService = Depends(get_recommendation_service),
) -> Response:
    background_tasks.add_task(
        service.recommend_by_review,
        request.review_id,
        request.review_content,
    )
    return Response(status_code=status.HTTP_202_ACCEPTED)
