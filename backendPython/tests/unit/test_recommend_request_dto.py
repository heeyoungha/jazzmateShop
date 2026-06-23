import pytest

from app.schemas.recommendation import RecommendByReviewRequest

from tests.fixtures import REVIEW_CONTENT, REVIEW_ID


USER_ID = "42"


def test_valid_request_maps_fields():
    """유효한 요청이면 review_id와 review_content가 그대로 매핑된다."""
    # given / when
    request = RecommendByReviewRequest(
        review_id=REVIEW_ID,
        review_content=REVIEW_CONTENT,
        user_id=USER_ID,
    )

    # then
    assert request.review_id == REVIEW_ID
    assert request.review_content == REVIEW_CONTENT


def test_review_content_trims_whitespace():
    """앞뒤 공백이 있는 본문은 trim 후 저장된다."""
    # given / when
    request = RecommendByReviewRequest(
        review_id=REVIEW_ID,
        review_content=f"  {REVIEW_CONTENT}  ",
        user_id=USER_ID,
    )

    # then
    assert request.review_content == REVIEW_CONTENT


def test_review_content_blank_raises_validation_error():
    """공백만 있는 본문은 ValueError를 발생시킨다."""
    # given / when / then
    with pytest.raises(ValueError):
        RecommendByReviewRequest(
            review_id=REVIEW_ID,
            review_content="   ",
            user_id=USER_ID,
        )


def test_missing_review_id_raises_validation_error():
    """review_id가 누락되면 ValueError를 발생시킨다."""
    # given / when / then
    with pytest.raises(ValueError):
        RecommendByReviewRequest(
            review_content=REVIEW_CONTENT,
            user_id=USER_ID,
        )


def test_missing_review_content_raises_validation_error():
    """review_content가 누락되면 ValueError를 발생시킨다."""
    # given / when / then
    with pytest.raises(ValueError):
        RecommendByReviewRequest(
            review_id=REVIEW_ID,
            user_id=USER_ID,
        )


def test_non_positive_review_id_raises_validation_error():
    """review_id가 0 이하이면 ValueError를 발생시킨다."""
    # given / when / then
    with pytest.raises(ValueError):
        RecommendByReviewRequest(
            review_id=0,
            review_content=REVIEW_CONTENT,
            user_id=USER_ID,
        )


def test_missing_user_id_raises_validation_error():
    """user_id가 누락되면 ValueError를 발생시킨다."""
    # given / when / then
    with pytest.raises(ValueError):
        RecommendByReviewRequest(review_id=REVIEW_ID, review_content=REVIEW_CONTENT)


def test_valid_request_maps_user_id():
    """유효한 요청이면 user_id가 그대로 매핑된다."""
    # given / when
    request = RecommendByReviewRequest(
        review_id=REVIEW_ID,
        review_content=REVIEW_CONTENT,
        user_id=USER_ID,
    )

    # then
    assert request.user_id == USER_ID


def test_user_id_trims_whitespace():
    """앞뒤 공백이 있는 user_id는 trim 후 저장된다."""
    # given / when
    request = RecommendByReviewRequest(
        review_id=REVIEW_ID,
        review_content=REVIEW_CONTENT,
        user_id=f"  {USER_ID}  ",
    )

    # then
    assert request.user_id == USER_ID


def test_user_id_blank_raises_validation_error():
    """공백만 있는 user_id는 ValueError를 발생시킨다."""
    # given / when / then
    with pytest.raises(ValueError):
        RecommendByReviewRequest(
            review_id=REVIEW_ID,
            review_content=REVIEW_CONTENT,
            user_id="   ",
        )
