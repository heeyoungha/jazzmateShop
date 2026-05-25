package shop.jazzmate.jazzmateshop.recommendation.dto;

import lombok.Builder;
import lombok.Getter;
import shop.jazzmate.jazzmateshop.recommendation.entity.RecommendAlbum;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@Builder
public class RecommendAlbumResponse {
    private Integer id;
    private Integer userReviewId;
    private Integer albumId;
    private BigDecimal recommendationScore;
    private String recommendationReason;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static RecommendAlbumResponse from(RecommendAlbum recommendation) {
        return RecommendAlbumResponse.builder()
                .id(recommendation.getId())
                .userReviewId(recommendation.getUserReviewId())
                .albumId(recommendation.getAlbumId())
                .recommendationScore(recommendation.getRecommendationScore())
                .recommendationReason(recommendation.getRecommendationReason())
                .createdAt(recommendation.getCreatedAt())
                .updatedAt(recommendation.getUpdatedAt())
                .build();
    }
}
