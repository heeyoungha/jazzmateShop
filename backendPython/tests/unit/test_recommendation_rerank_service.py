import pytest

from app.schemas.recommendation import AlbumCandidate, AlbumMetadata
from app.services.recommendation_rerank_service import RecommendationRerankService

ALBUM_REF_ID_1 = "00000000-0000-0000-0000-000000000101"
ALBUM_REF_ID_2 = "00000000-0000-0000-0000-000000000205"
MB_ALBUM_GID_1 = "00000000-0000-0000-0000-000000001001"
MB_ALBUM_GID_2 = "00000000-0000-0000-0000-000000001002"


def candidate(album_id: str, similarity: float) -> AlbumCandidate:
    return AlbumCandidate(
        album_id=album_id,
        similarity=similarity,
        album_title=f"Album {album_id}",
        artist_name="",
        critics_review_id=f"review-{album_id}",
    )


def metadata(
    album_id: str,
    artist_name: str | None,
    genres: list[str],
    first_release_year: int | None,
) -> AlbumMetadata:
    return AlbumMetadata(
        album_id=album_id,
        artist_name=artist_name,
        genres=genres,
        first_release_year=first_release_year,
    )


def test_rerank_promotes_candidate_matching_user_metadata():
    """벡터 점수가 근접하면 사용자 메타 취향과 맞는 후보를 위로 올린다."""
    # given
    service = RecommendationRerankService()
    candidates = [
        candidate(ALBUM_REF_ID_1, 0.91),
        candidate(ALBUM_REF_ID_2, 0.90),
    ]
    user_metadata = [
        metadata("user-1", "Wayne Shorter", ["post-bop", "hard bop"], 1966),
    ]
    candidate_metadata = {
        ALBUM_REF_ID_1: metadata(MB_ALBUM_GID_1, "Other Artist", ["smooth jazz"], 1985),
        ALBUM_REF_ID_2: metadata(MB_ALBUM_GID_2, "Wayne Shorter", ["post-bop"], 1965),
    }

    # when
    result = service.rerank(candidates, user_metadata, candidate_metadata, top_k=2)

    # then
    assert [item.album_id for item in result] == [ALBUM_REF_ID_2, ALBUM_REF_ID_1]
    assert result[0].similarity > result[1].similarity


def test_rerank_keeps_vector_order_when_user_metadata_is_empty():
    """사용자 메타 프로필이 없으면 기존 벡터 순서를 유지한다."""
    # given
    service = RecommendationRerankService()
    candidates = [
        candidate(ALBUM_REF_ID_1, 0.91),
        candidate(ALBUM_REF_ID_2, 0.90),
    ]

    # when
    result = service.rerank(candidates, [], {}, top_k=1)

    # then
    assert [item.album_id for item in result] == [ALBUM_REF_ID_1]
    assert result[0].similarity == pytest.approx(0.91)


def test_rerank_uses_vector_score_when_candidate_metadata_is_missing():
    """후보 메타가 없으면 해당 후보는 벡터 점수만 사용한다."""
    # given
    service = RecommendationRerankService()
    candidates = [
        candidate(ALBUM_REF_ID_1, 0.91),
        candidate(ALBUM_REF_ID_2, 0.90),
    ]
    user_metadata = [
        metadata("user-1", "Miles Davis", ["modal jazz"], 1959),
    ]

    # when
    result = service.rerank(candidates, user_metadata, {}, top_k=2)

    # then
    assert [item.album_id for item in result] == [ALBUM_REF_ID_1, ALBUM_REF_ID_2]
    assert [item.similarity for item in result] == pytest.approx([0.91, 0.90])
