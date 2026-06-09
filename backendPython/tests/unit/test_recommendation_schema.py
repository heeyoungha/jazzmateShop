from decimal import Decimal

from app.schemas.recommendation import (
    RecommendByReviewRequest,
    RecommendationCallbackItem,
    RecommendationCallbackRequest,
)

from app.core.error_codes import RecommendationErrorCode

from tests.fixtures import ALBUM_ID_1, REVIEW_CONTENT, REVIEW_ID, dump_alias


def test_request_valid_maps_fields():
    """Spring에서 받은 요청 필드명(snake_case)이 직렬화 후에도 그대로 유지된다.
    camelCase alias가 실수로 추가되면 Spring 요청 파싱이 깨지므로 이를 방지한다."""
    request = RecommendByReviewRequest(
        review_id=REVIEW_ID,
        review_content=REVIEW_CONTENT,
    )

    assert dump_alias(request) == {
        "review_id": REVIEW_ID,
        "review_content": REVIEW_CONTENT,
    }


def test_callback_item_serializes_camel_case():
    """Spring 콜백 페이로드의 각 추천 항목은 Java 컨벤션인 camelCase로 직렬화된다.
    snake_case로 보내면 Spring의 @RequestBody 역직렬화가 실패하므로 키 이름을 고정한다."""
    item = RecommendationCallbackItem(
        album_id=ALBUM_ID_1,
        recommendation_score=Decimal("0.9423"),
        recommendation_reason="감상문과 앨범 모두 차분한 모달 재즈의 분위기를 공유합니다.",
    )

    assert dump_alias(item) == {
        "albumId": ALBUM_ID_1,
        "recommendationScore": Decimal("0.9423"),
        "recommendationReason": "감상문과 앨범 모두 차분한 모달 재즈의 분위기를 공유합니다.",
    }


def test_callback_request_completed_contains_recommendations():
    """추천 성공 시 Spring에 보내는 콜백 페이로드 구조 검증
    Spring은 status 값으로 성공/실패를 분기하므로 페이로드 구조가 계약과 일치해야 한다."""
    item = RecommendationCallbackItem(
        album_id=ALBUM_ID_1,
        recommendation_score=Decimal("0.9423"),
        recommendation_reason="감상문과 앨범 모두 차분한 모달 재즈의 분위기를 공유합니다.",
    )

    request = RecommendationCallbackRequest.completed([item])
    payload = dump_alias(request)

    assert payload["status"] == "COMPLETED"
    assert payload["recommendations"] == [dump_alias(item)]
    assert payload["errorCode"] is None
    assert payload["message"] is None


def test_callback_request_failed_contains_error_and_empty_recommendations():
    """추천 실패 시 Spring에 보내는 콜백 페이로드 구조 검증.
    Spring은 errorCode로 실패 원인을 처리하므로 누락되거나 null이면 안 된다."""
    request = RecommendationCallbackRequest.failed(
        error_code=RecommendationErrorCode.NO_CANDIDATES,
        message="추천 후보가 없습니다.",
    )

    assert dump_alias(request) == {
        "status": "FAILED",
        "recommendations": [],
        "errorCode": RecommendationErrorCode.NO_CANDIDATES,
        "message": "추천 후보가 없습니다.",
    }
