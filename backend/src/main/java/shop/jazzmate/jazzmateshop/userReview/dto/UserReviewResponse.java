package shop.jazzmate.jazzmateshop.userReview.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserReviewResponse {
    private Integer id;
    private Integer albumId;
    private String userId;
    private String trackName;
    private String artistName; // 새로 추가
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
}
