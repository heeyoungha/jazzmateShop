import asyncio
import os
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field


class RecommendByReviewRequest(BaseModel):
    review_id: int = Field(gt=0)
    review_content: str = Field(min_length=1)


app = FastAPI(title="JazzmateShop Mock AI API")

SPRING_BASE_URL = os.getenv("SPRING_BASE_URL", "http://java-backend:8080").rstrip("/")
EMBEDDING_DELAY_SECONDS = int(os.getenv("MOCK_EMBEDDING_DELAY_MS", "300")) / 1000
REASON_DELAY_SECONDS = int(os.getenv("MOCK_REASON_DELAY_MS", "700")) / 1000
CALLBACK_TIMEOUT_SECONDS = float(os.getenv("MOCK_CALLBACK_TIMEOUT_SECONDS", "10"))
RECOMMENDATION_COUNT = int(os.getenv("MOCK_RECOMMENDATION_COUNT", "5"))


def build_recommendations() -> list[dict[str, Any]]:
    recommendations = []
    for index in range(RECOMMENDATION_COUNT):
        suffix = index + 1
        recommendations.append(
            {
                "albumId": f"00000000-0000-0000-0000-{suffix:012d}",
                "albumArtist": "Jazzmate Mock Artist",
                "albumTitle": f"Mock Recommendation Album {suffix}",
                "recommendationScore": round(0.95 - (index * 0.03), 4),
                "recommendationReason": "Mock recommendation reason for structural load testing.",
                "criticsReviewId": f"10000000-0000-0000-0000-{suffix:012d}",
            }
        )
    return recommendations


async def complete_recommendation(review_id: int) -> None:
    await asyncio.sleep(EMBEDDING_DELAY_SECONDS)
    await asyncio.sleep(REASON_DELAY_SECONDS)

    payload = {
        "status": "COMPLETED",
        "recommendations": build_recommendations(),
        "errorCode": None,
        "message": None,
    }

    async with httpx.AsyncClient(timeout=CALLBACK_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{SPRING_BASE_URL}/api/user-reviews/{review_id}/recommendations",
            json=payload,
        )
        response.raise_for_status()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/recommend/review", status_code=202)
async def recommend_by_review(
    request: RecommendByReviewRequest, background_tasks: BackgroundTasks
) -> dict[str, str]:
    if not request.review_content.strip():
        raise HTTPException(status_code=400, detail="review_content is required")

    background_tasks.add_task(complete_recommendation, request.review_id)
    return {"status": "accepted"}
