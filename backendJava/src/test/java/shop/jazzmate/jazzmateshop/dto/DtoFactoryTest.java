package shop.jazzmate.jazzmateshop.dto;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import shop.jazzmate.jazzmateshop.recommendation.entity.RecommendAlbum;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewSummaryResponse;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class DtoFactoryTest {

    // 모든 중첩 클래스에서 공유하는 픽스처
    private final RecommendAlbum REC = RecommendAlbum.builder()
            .id(100)
            .userReviewId(1)
            .albumId(10)
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
            assertThat(resp.getRecommendations().get(0).getAlbumId()).isEqualTo(10);
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
