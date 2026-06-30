from decimal import Decimal

import pytest

from app.schemas.recommendation import (
    AlbumCandidate,
    RecommendByReviewRequest,
    RecommendationCallbackItem,
    RecommendationCallbackRequest,
)

from app.core.error_codes import RecommendationErrorCode

from tests.fixtures import (ALBUM_ID_1,
    CRITICS_REVIEW_ID_1,
    REVIEW_CONTENT,
    REVIEW_ID,
    dump_alias,
)

USER_ID = "42"


def test_request_valid_maps_fields():
    """Spring에서 받은 요청 필드명(snake_case)이 직렬화 후에도 그대로 유지된다.
    camelCase alias가 실수로 추가되면 Spring 요청 파싱이 깨지므로 이를 방지한다."""
    # given / when
    request = RecommendByReviewRequest(
        review_id=REVIEW_ID,
        review_content=REVIEW_CONTENT,
        user_id=USER_ID,
    )

    # then
    assert dump_alias(request) == {
        "review_id": REVIEW_ID,
        "review_content": REVIEW_CONTENT,
        "user_id": USER_ID,
    }


def test_callback_item_serializes_camel_case():
    """Spring 콜백 페이로드의 각 추천 항목은 Java 컨벤션인 camelCase로 직렬화된다.
    snake_case로 보내면 Spring의 @RequestBody 역직렬화가 실패하므로 키 이름을 고정한다."""
    # given / when
    item = RecommendationCallbackItem(
        album_id=ALBUM_ID_1,
        album_artist="Miles Davis",
        album_title="Kind of Blue",
        recommendation_score=Decimal("0.9423"),
        recommendation_reason="감상문과 앨범 모두 차분한 모달 재즈의 분위기를 공유합니다.",
        critics_review_id=CRITICS_REVIEW_ID_1,
    )

    # then
    assert dump_alias(item) == {
        "albumId": ALBUM_ID_1,
        "albumArtist": "Miles Davis",
        "albumTitle": "Kind of Blue",
        "recommendationScore": Decimal("0.9423"),
        "recommendationReason": "감상문과 앨범 모두 차분한 모달 재즈의 분위기를 공유합니다.",
        "criticsReviewId": CRITICS_REVIEW_ID_1,
    }


def test_callback_request_completed_contains_recommendations():
    """추천 성공 시 Spring에 보내는 콜백 페이로드 구조 검증
    Spring은 status 값으로 성공/실패를 분기하므로 페이로드 구조가 계약과 일치해야 한다."""
    # given
    item = RecommendationCallbackItem(
        album_id=ALBUM_ID_1,
        album_artist="Miles Davis",
        album_title="Kind of Blue",
        recommendation_score=Decimal("0.9423"),
        recommendation_reason="감상문과 앨범 모두 차분한 모달 재즈의 분위기를 공유합니다.",
        critics_review_id=CRITICS_REVIEW_ID_1,
    )

    # when
    request = RecommendationCallbackRequest.completed([item])
    payload = dump_alias(request)

    # then
    assert payload["status"] == "COMPLETED"
    assert payload["recommendations"] == [dump_alias(item)]
    assert payload["errorCode"] is None
    assert payload["message"] is None


def test_callback_request_failed_contains_error_and_empty_recommendations():
    """추천 실패 시 Spring에 보내는 콜백 페이로드 구조 검증.
    Spring은 errorCode로 실패 원인을 처리하므로 누락되거나 null이면 안 된다."""
    # given / when
    request = RecommendationCallbackRequest.failed(
        error_code=RecommendationErrorCode.NO_CANDIDATES,
        message="추천 후보가 없습니다.",
    )

    # then
    assert dump_alias(request) == {
        "status": "FAILED",
        "recommendations": [],
        "errorCode": RecommendationErrorCode.NO_CANDIDATES,
        "message": "추천 후보가 없습니다.",
        "reviewEmbedding": None,
    }


def test_callback_request_completed_rejects_error_details():
    """성공 콜백은 실패 사유 필드를 함께 보낼 수 없다."""
    # given
    item = RecommendationCallbackItem(
        album_id=ALBUM_ID_1,
        album_artist="Miles Davis",
        album_title="Kind of Blue",
        recommendation_score=Decimal("0.9423"),
        recommendation_reason="감상문과 앨범 모두 차분한 모달 재즈의 분위기를 공유합니다.",
        critics_review_id=CRITICS_REVIEW_ID_1,
    )

    # when / then
    with pytest.raises(ValueError, match="completed callback"):
        RecommendationCallbackRequest(
            status="COMPLETED",
            recommendations=[item],
            error_code=RecommendationErrorCode.NO_CANDIDATES,
        )


def test_callback_request_failed_requires_error_details():
    """실패 콜백은 errorCode와 message를 반드시 포함해야 한다."""
    # given / when / then
    with pytest.raises(ValueError, match="failed callback requires"):
        RecommendationCallbackRequest(status="FAILED", recommendations=[])


def test_callback_request_failed_rejects_recommendations():
    """실패 콜백은 추천 목록을 함께 보낼 수 없다."""
    # given
    item = RecommendationCallbackItem(
        album_id=ALBUM_ID_1,
        album_artist="Miles Davis",
        album_title="Kind of Blue",
        recommendation_score=Decimal("0.9423"),
        recommendation_reason="감상문과 앨범 모두 차분한 모달 재즈의 분위기를 공유합니다.",
        critics_review_id=CRITICS_REVIEW_ID_1,
    )

    # when / then
    with pytest.raises(ValueError, match="must not include recommendations"):
        RecommendationCallbackRequest(
            status="FAILED",
            recommendations=[item],
            error_code=RecommendationErrorCode.NO_CANDIDATES,
            message="추천 후보가 없습니다.",
        )


@pytest.mark.parametrize(
    "field_name, value",
    [
        ("album_artist", ""),
        ("album_title", " "),
        ("recommendation_reason", ""),
        ("critics_review_id", ""),
    ],
)
def test_callback_item_requires_completed_display_fields(field_name, value):
    """완료 콜백 항목은 화면 표시와 평론가 리뷰 연결에 필요한 필드를 반드시 포함한다."""
    values = {
        "album_id": ALBUM_ID_1,
        "album_artist": "Miles Davis",
        "album_title": "Kind of Blue",
        "recommendation_score": Decimal("0.9423"),
        "recommendation_reason": "감상문과 앨범 모두 차분한 모달 재즈의 분위기를 공유합니다.",
        "critics_review_id": CRITICS_REVIEW_ID_1,
    }
    values[field_name] = value

    with pytest.raises(ValueError, match=field_name):
        RecommendationCallbackItem(**values)


def test_album_candidate_from_row_requires_album_id():
    """DB row에 album_id가 없으면 빈 문자열 후보를 만들지 않는다."""
    # given / when / then
    with pytest.raises(ValueError, match="album_id"):
        AlbumCandidate.from_row(
            {"similarity": 0.9, "critics_review_id": CRITICS_REVIEW_ID_1}
        )


def test_album_candidate_from_row_requires_critics_review_id():
    """DB row에 critics_review_id가 없으면 콜백 불가능한 후보를 만들지 않는다."""
    # given / when / then
    with pytest.raises(ValueError, match="critics_review_id"):
        AlbumCandidate.from_row({"album_id": ALBUM_ID_1, "similarity": 0.9})
