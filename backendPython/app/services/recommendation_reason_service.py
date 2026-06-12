import asyncio
from typing import Any, Iterable, List

from app.core.config import settings
from app.core.exceptions import ConfigurationError
from app.schemas.recommendation import AlbumCandidate, RecommendationReason


class RecommendationReasonService:
    def __init__(self, openai_client: Any):
        if openai_client is None:
            raise ConfigurationError(
                "RecommendationReasonService requires an openai client."
            )
        self.openai_client = openai_client

    async def generate_reasons(
        self, review_content: str, candidates: Iterable[AlbumCandidate]
    ) -> List[RecommendationReason]:
        candidate_list = list(candidates)
        return await asyncio.gather(
            *[
                self._generate_reason(review_content, candidate)
                for candidate in candidate_list
            ]
        )

    async def _generate_reason(
        self, review_content: str, candidate: AlbumCandidate
    ) -> RecommendationReason:
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                messages=self._build_messages(review_content, candidate),
            )
            content = response.choices[0].message.content.strip()
            if not content:
                content = self.build_fallback_reason(review_content, candidate)
        except Exception:
            content = self.build_fallback_reason(review_content, candidate)

        return RecommendationReason(
            album_id=candidate.album_id,
            recommendation_reason=content,
        )

    def _build_messages(
        self, review_content: str, candidate: AlbumCandidate
    ) -> list[dict[str, str]]:
        user_prompt = (
            f"사용자 감상문: {review_content}\n"
            f"앨범: {candidate.artist_name} - {candidate.album_title}\n"
            f"전문가 리뷰 요약: {candidate.review_summary}\n"
            f"전문가 리뷰 원문 일부: {candidate.review_content}\n"
            "이 감상문과 앨범이 어울리는 이유를 짧은 한국어 문장으로 작성해 주세요."
        )
        return [
            {
                "role": "system",
                "content": "재즈 앨범 추천 사유를 간결하고 구체적인 한국어로 작성한다.",
            },
            {"role": "user", "content": user_prompt},
        ]

    def build_fallback_reason(
        self, review_content: str, candidate: AlbumCandidate
    ) -> str:
        combined = f"{review_content} {candidate.review_summary} {candidate.review_content}"
        if "차분" in combined:
            feature = "차분한 분위기"
        elif "modal" in combined.lower() or "모달" in combined:
            feature = "모달 재즈의 색채"
        elif "공간" in combined:
            feature = "넓은 공간감"
        else:
            feature = "감상문과 맞닿은 음악적 분위기"

        album = candidate.album_title or "이 앨범"
        return f"{album}은 {feature}가 잘 드러나 추천할 만합니다."
