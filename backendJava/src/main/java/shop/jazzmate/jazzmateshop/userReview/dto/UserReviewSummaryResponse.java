package shop.jazzmate.jazzmateshop.userReview.dto;

import lombok.Builder;
import lombok.Getter;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@Builder
public class UserReviewSummaryResponse {
    private Integer id;
    private String trackName;
    private String artistName;
    private String reviewContent;
    private BigDecimal rating;
    private String mood;
    private String genre;
    private LocalDateTime createdAt;

    public static UserReviewSummaryResponse from(UserReview review) {
        return UserReviewSummaryResponse.builder()
                .id(review.getId())
                .trackName(review.getTrackName())
                .artistName(review.getArtistName())
                .reviewContent(review.getReviewContent())
                .rating(review.getRating())
                .mood(review.getMood())
                .genre(review.getGenre())
                .createdAt(review.getCreatedAt())
                .build();
    }
}
