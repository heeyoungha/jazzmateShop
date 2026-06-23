import importlib

import pytest

from app.core.config import settings


def service_class():
    module = importlib.import_module("app.services.taste_vector_service")
    return module.TasteVectorService


def embedding(first: float, second: float) -> list[float]:
    return [first, second] + [0.0] * (settings.EMBEDDING_DIMENSIONS - 2)


# 리뷰 임베딩(60%)과 사용자 청취 앨범 평균 벡터(40%)를 가중 합산하여 쿼리 벡터를 생성한다
def test_merges_review_and_user_taste_vectors_with_60_40_weights():
    # given
    service = service_class()(review_weight=0.6, taste_weight=0.4)

    # when
    result = service.build_query_vector(
        review_embedding=embedding(0.2, 0.4),
        reviewed_album_embeddings=[
            embedding(0.6, 0.8),
            embedding(0.4, 0.6),
        ],
    )

    # then
    assert result == pytest.approx(embedding(0.32, 0.52))


# 사용자의 청취 이력이 없을 경우 리뷰 임베딩을 그대로 쿼리 벡터로 사용한다
def test_uses_review_embedding_when_user_has_no_matched_albums():
    # given
    service = service_class()(review_weight=0.6, taste_weight=0.4)

    # when
    result = service.build_query_vector(
        review_embedding=embedding(0.2, 0.4),
        reviewed_album_embeddings=[],
    )

    # then
    assert result == embedding(0.2, 0.4)


def test_rejects_invalid_review_embedding_dimensions():
    # given
    service = service_class()()

    # when / then
    with pytest.raises(ValueError, match="invalid dimensions"):
        service.build_query_vector(
            review_embedding=[0.2, 0.4],
            reviewed_album_embeddings=[],
        )


def test_rejects_invalid_reviewed_album_embedding_dimensions():
    # given
    service = service_class()()

    # when / then
    with pytest.raises(ValueError, match="invalid dimensions"):
        service.build_query_vector(
            review_embedding=embedding(0.2, 0.4),
            reviewed_album_embeddings=[[0.6, 0.8]],
        )


def test_rejects_negative_weights():
    # given / when / then
    with pytest.raises(ValueError, match="non-negative"):
        service_class()(review_weight=-0.1, taste_weight=1.1)


def test_rejects_weights_that_do_not_sum_to_one():
    # given / when / then
    with pytest.raises(ValueError, match="sum to 1"):
        service_class()(review_weight=0.6, taste_weight=0.5)
