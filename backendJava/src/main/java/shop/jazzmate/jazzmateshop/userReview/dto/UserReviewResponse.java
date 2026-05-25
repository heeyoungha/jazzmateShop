package shop.jazzmate.jazzmateshop.userReview.dto;

import lombok.Builder;
import lombok.Getter;
import shop.jazzmate.jazzmateshop.recommendation.dto.RecommendAlbumResponse;
import shop.jazzmate.jazzmateshop.recommendation.entity.RecommendAlbum;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendationStatus;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Getter
@Builder
public class UserReviewResponse {
    private UserReviewDetail review;
    private RecommendationStatus recommendationStatus;
    private boolean hasRecommendations;
    private List<RecommendAlbumResponse> recommendations;

    // GET /{id} 상세 응답용 — recommendations 포함
    public static UserReviewResponse from(UserReview userReview, List<RecommendAlbum> recommendations) {
        return UserReviewResponse.builder()
                .review(UserReviewDetail.from(userReview))
                .recommendationStatus(userReview.getRecommendationStatus())
                .hasRecommendations(!recommendations.isEmpty())
                .recommendations(recommendations.stream()
                        .map(RecommendAlbumResponse::from)
                        .toList())
                .build();
    }

    @Getter
    @Builder
    public static class UserReviewDetail {
        private Integer id;
        private String userId;
        private String trackName;
        private String artistName;
        private String reviewContent;
        private BigDecimal rating;
        private String mood;
        private String genre;
        private BigDecimal energyLevel;
        private Integer bpm;
        private String vocalStyle;
        private String instrumentation;
        private Boolean isPublic;
        private Boolean isFeatured;
        private Integer likeCount;
        private Integer commentCount;
        private LocalDateTime createdAt;
        private LocalDateTime updatedAt;

        public static UserReviewDetail from(UserReview userReview) {
            return UserReviewDetail.builder()
                    .id(userReview.getId())
                    .userId(userReview.getUserId())
                    .trackName(userReview.getTrackName())
                    .artistName(userReview.getArtistName())
                    .reviewContent(userReview.getReviewContent())
                    .rating(userReview.getRating())
                    .mood(userReview.getMood())
                    .genre(userReview.getGenre())
                    .energyLevel(userReview.getEnergyLevel())
                    .bpm(userReview.getBpm())
                    .vocalStyle(userReview.getVocalStyle())
                    .instrumentation(userReview.getInstrumentation())
                    .isPublic(userReview.getIsPublic())
                    .isFeatured(userReview.getIsFeatured())
                    .likeCount(userReview.getLikeCount())
                    .commentCount(userReview.getCommentCount())
                    .createdAt(userReview.getCreatedAt())
                    .updatedAt(userReview.getUpdatedAt())
                    .build();
        }
    }
}
