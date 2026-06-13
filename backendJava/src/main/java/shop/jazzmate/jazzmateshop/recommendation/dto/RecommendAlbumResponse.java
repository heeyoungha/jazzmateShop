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
    private String albumId;
    private String albumTitle;
    private String albumArtist;
    private String criticsReviewId;
    private String criticsReviewUrl;
    private BigDecimal recommendationScore;
    private String recommendationReason;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    private static final String CRITICS_REVIEW_URL_PREFIX = "/critics/";

    public static RecommendAlbumResponse from(RecommendAlbum recommendation) {
        String albumId = recommendation.getAlbumId() != null
                ? recommendation.getAlbumId().toString()
                : null;
        String criticsReviewId = recommendation.getCriticsReviewId() != null
                ? recommendation.getCriticsReviewId().toString()
                : null;
        String criticsReviewUrl = criticsReviewId != null
                ? CRITICS_REVIEW_URL_PREFIX + criticsReviewId
                : null;

        return RecommendAlbumResponse.builder()
                .id(recommendation.getId())
                .userReviewId(recommendation.getUserReviewId())
                .albumId(albumId)
                .albumTitle(recommendation.getAlbumTitle())
                .albumArtist(recommendation.getAlbumArtist())
                .criticsReviewId(criticsReviewId)
                .criticsReviewUrl(criticsReviewUrl)
                .recommendationScore(recommendation.getRecommendationScore())
                .recommendationReason(recommendation.getRecommendationReason())
                .createdAt(recommendation.getCreatedAt())
                .updatedAt(recommendation.getUpdatedAt())
                .build();
    }
}
