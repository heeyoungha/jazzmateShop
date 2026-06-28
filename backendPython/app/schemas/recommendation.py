from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.error_codes import RecommendationErrorCode


NonBlankStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


# FastAPI가 Spring Boot의 추천 요청 본문을 검증할 때 사용한다.
class RecommendByReviewRequest(BaseModel):
    review_id: int = Field(gt=0)
    review_content: NonBlankStr
    user_id: NonBlankStr


# Spring Boot 콜백에 담을 추천 앨범 1건의 JSON payload를 만들 때 사용한다.
class RecommendationCallbackItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=False)

    album_id: NonBlankStr = Field(alias="albumId")
    album_artist: NonBlankStr = Field(alias="albumArtist")
    album_title: NonBlankStr = Field(alias="albumTitle")
    recommendation_score: Decimal = Field(alias="recommendationScore")
    recommendation_reason: NonBlankStr = Field(alias="recommendationReason")
    critics_review_id: NonBlankStr = Field(alias="criticsReviewId")


# Spring Boot 콜백의 성공/실패 전체 JSON payload를 만들 때 사용한다.
class RecommendationCallbackRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=False)

    status: Literal["COMPLETED", "FAILED"]
    recommendations: list[RecommendationCallbackItem]
    error_code: RecommendationErrorCode | None = Field(
        default=None, alias="errorCode"
    )
    message: str | None = None

    @model_validator(mode="after")
    def validate_status_payload(self) -> "RecommendationCallbackRequest":
        if self.status == "COMPLETED":
            if self.error_code is not None or self.message is not None:
                raise ValueError("completed callback must not include error details.")
            return self

        if self.error_code is None or not self.message:
            raise ValueError("failed callback requires error_code and message.")
        if self.recommendations:
            raise ValueError("failed callback must not include recommendations.")
        return self

    @classmethod
    def completed(
        cls, recommendations: Iterable[RecommendationCallbackItem]
    ) -> "RecommendationCallbackRequest":
        return cls(status="COMPLETED", recommendations=list(recommendations))

    @classmethod
    def failed(
        cls, error_code: RecommendationErrorCode, message: str
    ) -> "RecommendationCallbackRequest":
        return cls(
            status="FAILED",
            recommendations=[],
            error_code=error_code,
            message=message,
        )


# DB 유사도 검색 결과 row를 서비스 내부 추천 후보로 넘길 때 사용한다.
class AlbumCandidate(BaseModel):
    album_id: NonBlankStr
    similarity: float
    album_title: str = ""
    artist_name: str = ""
    review_summary: str = ""
    review_content: str = ""
    critics_review_id: NonBlankStr

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AlbumCandidate":
        return cls(
            album_id=row.get("album_id"),
            similarity=float(row.get("similarity", 0)),
            album_title=str(row.get("album_title", "")),
            artist_name=str(row.get("artist_name") or row.get("album_artist", "")),
            review_summary=str(row.get("review_summary", "")),
            review_content=str(row.get("review_content", "")),
            critics_review_id=row.get("critics_review_id"),
        )


# LLM이 생성한 앨범별 추천 사유를 후보 앨범과 매칭할 때 사용한다.
@dataclass
class RecommendationReason:
    album_id: str
    recommendation_reason: str


@dataclass(frozen=True)
class AlbumMetadata:
    album_id: str
    artist_name: str | None
    genres: tuple[str, ...]
    first_release_year: int | None


def normalize_score(value: float) -> Decimal:
    bounded = min(max(float(value), 0.0), 1.0)
    return Decimal(str(bounded)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
