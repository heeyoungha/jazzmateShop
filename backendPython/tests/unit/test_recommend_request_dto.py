import pytest

from app.schemas.recommendation import RecommendByReviewRequest

from tests.fixtures import REVIEW_CONTENT, REVIEW_ID


def test_valid_request_maps_fields():
    """유효한 요청이면 review_id와 review_content가 그대로 매핑된다."""
    request = RecommendByReviewRequest(
        review_id=REVIEW_ID,
        review_content=REVIEW_CONTENT,
    )

    assert request.review_id == REVIEW_ID
    assert request.review_content == REVIEW_CONTENT


def test_review_content_trims_whitespace():
    """앞뒤 공백이 있는 본문은 trim 후 저장된다."""
    request = RecommendByReviewRequest(
        review_id=REVIEW_ID,
        review_content=f"  {REVIEW_CONTENT}  ",
    )

    assert request.review_content == REVIEW_CONTENT


def test_review_content_blank_raises_validation_error():
    """공백만 있는 본문은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        RecommendByReviewRequest(review_id=REVIEW_ID, review_content="   ")


def test_missing_review_id_raises_validation_error():
    """review_id가 누락되면 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        RecommendByReviewRequest(review_content=REVIEW_CONTENT)


def test_missing_review_content_raises_validation_error():
    """review_content가 누락되면 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        RecommendByReviewRequest(review_id=REVIEW_ID)


def test_non_positive_review_id_raises_validation_error():
    """review_id가 0 이하이면 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        RecommendByReviewRequest(review_id=0, review_content=REVIEW_CONTENT)
