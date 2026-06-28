from collections import Counter
from dataclasses import dataclass
from statistics import median

from app.schemas.recommendation import AlbumCandidate, AlbumMetadata


def _normalize(value: str | None) -> str:
    """메타데이터 비교를 위해 문자열을 공백 제거 + 소문자로 정규화한다."""
    return (value or "").strip().lower()


def _bounded_score(value: float) -> float:
    """벡터 유사도 점수를 0.0~1.0 범위로 제한한다."""
    return min(max(float(value), 0.0), 1.0)


@dataclass(frozen=True)
class TasteMetadataProfile:
    artists: Counter[str]
    genres: Counter[str]
    median_year: int | None

    @property
    def is_empty(self) -> bool:
        """사용자 취향 메타데이터가 rerank에 쓸 수 없는 상태인지 확인한다."""
        return not self.artists and not self.genres and self.median_year is None

    @property
    def max_artist_count(self) -> int:
        """아티스트 매칭 점수를 0~1로 정규화하기 위한 최대 등장 횟수다."""
        return max(self.artists.values(), default=1)

    @property
    def max_genre_count(self) -> int:
        """장르 매칭 점수를 0~1로 정규화하기 위한 최대 등장 횟수다."""
        return max(self.genres.values(), default=1)

    @classmethod
    def from_metadata(
        cls, metadata_items: list[AlbumMetadata]
    ) -> "TasteMetadataProfile":
        """
        사용자가 들은 앨범 메타데이터 목록을 취향 프로필로 집계한다.

        예시 반환값:
            # first_release_year 값이 [1959, 1965, 1966]이면 중앙값은 1965다.
            TasteMetadataProfile(
                artists=Counter({"wayne shorter": 2, "miles davis": 1}),
                genres=Counter({"post-bop": 2, "modal jazz": 1}),
                median_year=1965,
            )
        """
        artists: Counter[str] = Counter(
            artist
            for metadata in metadata_items
            if (artist := _normalize(metadata.artist_name))
        )
        genres: Counter[str] = Counter(
            genre
            for metadata in metadata_items
            for raw_genre in metadata.genres
            if (genre := _normalize(raw_genre))
        )
        years = [
            metadata.first_release_year
            for metadata in metadata_items
            if metadata.first_release_year is not None
        ]

        return cls(
            artists=artists,
            genres=genres,
            median_year=int(median(years)) if years else None,
        )


class RecommendationRerankService:
    def __init__(
        self,
        vector_weight: float = 0.8,
        meta_weight: float = 0.2,
        artist_weight: float = 0.25,
        genre_weight: float = 0.55,
        era_weight: float = 0.20,
    ):
        """벡터 점수와 메타데이터 점수의 가중치를 설정한다."""
        self.vector_weight = vector_weight
        self.meta_weight = meta_weight
        self.artist_weight = artist_weight
        self.genre_weight = genre_weight
        self.era_weight = era_weight

    def rerank(
        self,
        candidates: list[AlbumCandidate],
        user_metadata: list[AlbumMetadata],
        candidate_metadata_by_album_id: dict[str, AlbumMetadata],
        top_k: int,
    ) -> list[AlbumCandidate]:
        """후보 앨범을 사용자 취향 메타데이터 점수를 반영해 다시 정렬한다."""
        profile = TasteMetadataProfile.from_metadata(user_metadata)
        if not candidates or profile.is_empty:
            return candidates[:top_k]

        scored_candidates = [
            self._copy_with_score(
                candidate=candidate,
                final_score=self._final_score(
                    candidate=candidate,
                    profile=profile,
                    metadata=candidate_metadata_by_album_id.get(candidate.album_id),
                ),
            )
            for candidate in candidates
        ]
        return sorted(
            scored_candidates,
            key=lambda candidate: candidate.similarity,
            reverse=True,
        )[:top_k]

    def _final_score(
        self,
        candidate: AlbumCandidate,
        profile: "TasteMetadataProfile",
        metadata: AlbumMetadata | None,
    ) -> float:
        """후보 1개의 최종 점수를 벡터 점수와 메타데이터 점수로 계산한다."""
        vector_score = _bounded_score(candidate.similarity)
        if metadata is None:
            return vector_score

        meta_score = self._metadata_score(profile, metadata)
        return vector_score * self.vector_weight + meta_score * self.meta_weight

    def _metadata_score(
        self, profile: TasteMetadataProfile, metadata: AlbumMetadata
    ) -> float:
        """아티스트, 장르, 발매연도 점수를 각각의 메타 가중치로 합산한다."""
        return (
            _artist_score(profile, metadata) * self.artist_weight
            + _genre_score(profile, metadata) * self.genre_weight
            + _era_score(profile, metadata) * self.era_weight
        )

    def _copy_with_score(
        self, candidate: AlbumCandidate, final_score: float
    ) -> AlbumCandidate:
        """원본 후보 객체를 변경하지 않고 similarity만 최종 점수로 교체한다."""
        copy_method = getattr(candidate, "model_copy", candidate.copy)
        return copy_method(update={"similarity": final_score})


def _artist_score(profile: TasteMetadataProfile, metadata: AlbumMetadata) -> float:
    """후보 아티스트가 사용자 취향 프로필에 많이 등장할수록 높은 점수를 준다."""
    artist = _normalize(metadata.artist_name)
    if not artist or artist not in profile.artists:
        return 0.0
    return profile.artists[artist] / profile.max_artist_count


def _genre_score(profile: TasteMetadataProfile, metadata: AlbumMetadata) -> float:
    """후보 장르가 사용자 취향 장르와 많이 겹칠수록 높은 점수를 준다."""
    candidate_genres = [
        genre
        for raw_genre in metadata.genres
        if (genre := _normalize(raw_genre))
    ]
    if not candidate_genres or not profile.genres:
        return 0.0

    matched_weight = sum(profile.genres.get(genre, 0) for genre in candidate_genres)
    max_weight = profile.max_genre_count * len(candidate_genres)
    return min(matched_weight / max_weight, 1.0)


def _era_score(profile: TasteMetadataProfile, metadata: AlbumMetadata) -> float:
    """사용자 취향의 중앙 발매연도와 가까운 후보일수록 높은 점수를 준다."""
    if profile.median_year is None or metadata.first_release_year is None:
        return 0.0

    year_diff = abs(metadata.first_release_year - profile.median_year)
    if year_diff <= 5:
        return 1.0
    if year_diff <= 10:
        return 0.7
    if year_diff <= 20:
        return 0.4
    return 0.0
