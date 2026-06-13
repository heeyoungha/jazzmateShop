package shop.jazzmate.jazzmateshop.dto;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import shop.jazzmate.jazzmateshop.criticsReview.dto.CriticsReviewResponse;
import shop.jazzmate.jazzmateshop.criticsReview.dto.CriticsReviewSummaryResponse;
import shop.jazzmate.jazzmateshop.criticsReview.entity.CriticsReview;
import shop.jazzmate.jazzmateshop.recommendation.entity.RecommendAlbum;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewSummaryResponse;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class DtoFactoryTest {

    private static final String RECOMMENDED_ALBUM_ID = "00000000-0000-0000-0000-000000000010";
    private static final UUID CRITICS_REVIEW_ID = UUID.fromString("00000000-0000-0000-0000-000000000020");

    // 모든 중첩 클래스에서 공유하는 픽스처
    private final RecommendAlbum REC = RecommendAlbum.builder()
            .id(100)
            .userReviewId(1)
            .albumId(UUID.fromString(RECOMMENDED_ALBUM_ID))
            .criticsReviewId(CRITICS_REVIEW_ID)
            .albumArtist("Miles Davis")
            .albumTitle("Kind of Blue")
            .recommendationScore(new BigDecimal("0.9800"))
            .recommendationReason("분위기 일치")
            .build();

    private final UserReview REVIEW = UserReview.builder()
            .id(1)
            .userId("user-001")
            .trackName("So What")
            .artistName("Miles Davis")
            .reviewContent("명반")
            .rating(new BigDecimal("4.5"))
            .mood("melancholic")
            .genre("modal jazz")
            .energyLevel(new BigDecimal("0.75"))
            .bpm(120)
            .isPublic(true)
            .isFeatured(false)
            .likeCount(0)
            .commentCount(0)
            .build();

    // ────────────────────────────────────────────────
    // UserReviewResponse.from(entity, recommendations)
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("UserReviewResponse.from(entity, recommendations) — 상세 응답용")
    class UserReviewResponseFromEntityAndRecommendations {

        @Test
        @DisplayName("recommendations 비어있으면 review 객체 존재, hasRecommendations=false")
        void from_emptyRecommendations_hasRecommendationsFalse() {
            UserReviewResponse resp = UserReviewResponse.from(REVIEW, List.of());

            assertThat(resp.getReview()).isNotNull();
            assertThat(resp.getReview().getId()).isEqualTo(1);
            assertThat(resp.isHasRecommendations()).isFalse();
            assertThat(resp.getRecommendations()).isEmpty();
        }

        @Test
        @DisplayName("recommendations 있으면 review 객체 존재, hasRecommendations=true, recommendations nested DTO로 변환")
        void from_withRecommendations_hasRecommendationsTrue() {
            UserReviewResponse resp = UserReviewResponse.from(REVIEW, List.of(REC));

            assertThat(resp.getReview()).isNotNull();
            assertThat(resp.getReview().getId()).isEqualTo(1);
            assertThat(resp.isHasRecommendations()).isTrue();
            assertThat(resp.getRecommendations()).hasSize(1);
            assertThat(resp.getRecommendations().get(0).getId()).isEqualTo(100);
            assertThat(resp.getRecommendations().get(0).getAlbumId()).isEqualTo(RECOMMENDED_ALBUM_ID);
            assertThat(resp.getRecommendations().get(0).getAlbumTitle()).isEqualTo("Kind of Blue");
            assertThat(resp.getRecommendations().get(0).getAlbumArtist()).isEqualTo("Miles Davis");
            assertThat(resp.getRecommendations().get(0).getRecommendationScore()).isEqualByComparingTo("0.9800");
            assertThat(resp.getRecommendations().get(0).getRecommendationReason()).isEqualTo("분위기 일치");
        }
    }

    // ────────────────────────────────────────────────
    // UserReviewSummaryResponse.from(entity)
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("UserReviewSummaryResponse.from(entity) — 목록 전용 8개 필드")
    class UserReviewSummaryResponseFactory {

        @Test
        @DisplayName("8개 필드만 포함 (id, trackName, artistName, reviewContent, rating, mood, genre, createdAt)")
        void from_mapsOnly8Fields() {
            UserReviewSummaryResponse summary = UserReviewSummaryResponse.from(REVIEW);

            assertThat(summary.getId()).isEqualTo(1);
            assertThat(summary.getTrackName()).isEqualTo("So What");
            assertThat(summary.getArtistName()).isEqualTo("Miles Davis");
            assertThat(summary.getReviewContent()).isEqualTo("명반");
            assertThat(summary.getRating()).isEqualByComparingTo("4.5");
            assertThat(summary.getMood()).isEqualTo("melancholic");
            assertThat(summary.getGenre()).isEqualTo("modal jazz");
            // createdAt은 @CreationTimestamp 자동 세팅이라 null 가능성 있음 (엔티티 미저장 상태)

            // SummaryResponse는 recommendations 필드가 없어야 함 (컴파일 레벨 보장)
            // hasRecommendations, recommendations 필드가 존재하지 않으므로
            // summary.getRecommendations() 같은 코드가 컴파일되면 명세 위반
        }
    }

    // ────────────────────────────────────────────────
    // ApiResponse 팩토리
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("ApiResponse 팩토리")
    class ApiResponseFactory {

        @Test
        @DisplayName("ok(message, data) → success=true, message, data 세팅")
        void ok_withData_setsSuccessTrueAndData() {
            var resp = shop.jazzmate.jazzmateshop.common.dto.ApiResponse.ok("성공", 42);

            assertThat(resp.isSuccess()).isTrue();
            assertThat(resp.getMessage()).isEqualTo("성공");
            assertThat(resp.getData()).isEqualTo(42);
        }

        @Test
        @DisplayName("ok(message) → success=true, message 세팅, data=null")
        void ok_withoutData_setsSuccessTrueAndDataNull() {
            var resp = shop.jazzmate.jazzmateshop.common.dto.ApiResponse.ok("성공");

            assertThat(resp.isSuccess()).isTrue();
            assertThat(resp.getMessage()).isEqualTo("성공");
            assertThat(resp.getData()).isNull();
        }

    }

    private final CriticsReview CRITICS = CriticsReview.builder()
            .id(UUID.fromString("00000000-0000-0000-0000-000000000001"))
            .title("Kind of Blue")
            .reviewer("AllAboutJazz")
            .reviewSummary("GPT 요약 내용")
            .reviewContent("원문 내용")
            .reviewUrl("https://example.com")
            .build();

    // ────────────────────────────────────────────────
    // CriticsReviewSummaryResponse.from(entity)
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("CriticsReviewSummaryResponse.from(entity) — 목록 전용")
    class CriticsReviewSummaryResponseFactory {

        @Test
        @DisplayName("목록 전용 필드만 매핑 (id, title, reviewer, reviewSummary)")
        void from_mapsOnlySummaryFields() {
            CriticsReviewSummaryResponse summary = CriticsReviewSummaryResponse.from(CRITICS);

            assertThat(summary.getId()).isEqualTo(CRITICS.getId());
            assertThat(summary.getTitle()).isEqualTo("Kind of Blue");
            assertThat(summary.getReviewer()).isEqualTo("AllAboutJazz");
            assertThat(summary.getReviewSummary()).isEqualTo("GPT 요약 내용");
        }
    }

    // ────────────────────────────────────────────────
    // CriticsReviewResponse.from(entity)
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("CriticsReviewResponse.from(entity) — 상세 응답용")
    class CriticsReviewResponseFactory {

        @Test
        @DisplayName("상세 필드 전체 매핑 (id, title, reviewer, reviewContent, reviewSummary, reviewUrl, createdAt)")
        void from_mapsOnlyDetailFields() {
            CriticsReviewResponse detail = CriticsReviewResponse.from(CRITICS);

            assertThat(detail.getId()).isEqualTo(CRITICS.getId());
            assertThat(detail.getTitle()).isEqualTo("Kind of Blue");
            assertThat(detail.getReviewer()).isEqualTo("AllAboutJazz");
            assertThat(detail.getReviewContent()).isEqualTo("원문 내용");
            assertThat(detail.getReviewSummary()).isEqualTo("GPT 요약 내용");
            assertThat(detail.getReviewUrl()).isEqualTo("https://example.com");
        }
    }

    // ────────────────────────────────────────────────
    // ErrorResponse
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("ErrorResponse")
    class ErrorResponseTest {

        @Test
        @DisplayName("success는 항상 false 고정")
        void errorResponse_successAlwaysFalse() {
            var err = new shop.jazzmate.jazzmateshop.common.dto.ErrorResponse("오류 발생");

            assertThat(err.isSuccess()).isFalse();
            assertThat(err.getMessage()).isEqualTo("오류 발생");
        }
    }

}
