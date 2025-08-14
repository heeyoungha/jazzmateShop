package shop.jazzmate.jazzmateshop.userReview.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendTrack;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserReviewWithRecommendationsResponse {
    private Integer id;
    private Integer albumId;
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
    private List<String> tags;
    private Boolean isPublic;
    private Boolean isFeatured;
    private Integer likeCount;
    private Integer commentCount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    
    // 추천 결과 포함
    private List<RecommendTrack> recommendations;
    private boolean hasRecommendations;
}