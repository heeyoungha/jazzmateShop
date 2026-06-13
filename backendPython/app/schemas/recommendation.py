from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Annotated, Any, Iterable, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.error_codes import RecommendationErrorCode


class RecommendByReviewRequest(BaseModel):
    review_id: Annotated[int, Field(gt=0)]
    review_content: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ]


class RecommendationCallbackItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=False)

    album_id: str = Field(alias="albumId")
    album_artist: Optional[str] = Field(default=None, alias="albumArtist")
    album_title: Optional[str] = Field(default=None, alias="albumTitle")
    recommendation_score: Decimal = Field(alias="recommendationScore")
    recommendation_reason: str = Field(alias="recommendationReason")
    critics_review_id: str = Field(alias="criticsReviewId")


class RecommendationCallbackRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=False)

    status: Literal["COMPLETED", "FAILED"]
    recommendations: List[RecommendationCallbackItem]
    error_code: Optional[RecommendationErrorCode] = Field(default=None, alias="errorCode")
    message: Optional[str] = None

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


@dataclass
class AlbumCandidate:
    album_id: str
    similarity: float
    album_title: str = ""
    artist_name: str = ""
    review_summary: str = ""
    review_content: str = ""
    critics_review_id: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AlbumCandidate":
        return cls(
            album_id=str(row.get("album_id", "")),
            similarity=float(row.get("similarity", 0)),
            album_title=str(row.get("album_title", "")),
            artist_name=str(row.get("artist_name") or row.get("album_artist", "")),
            review_summary=str(row.get("review_summary", "")),
            review_content=str(row.get("review_content", "")),
            critics_review_id=str(row.get("critics_review_id", "")),
        )


@dataclass
class RecommendationReason:
    album_id: str
    recommendation_reason: str


def normalize_score(value: float) -> Decimal:
    bounded = min(max(float(value), 0.0), 1.0)
    return Decimal(str(bounded)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
