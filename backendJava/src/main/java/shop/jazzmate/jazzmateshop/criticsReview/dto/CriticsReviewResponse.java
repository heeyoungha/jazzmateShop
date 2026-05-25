package shop.jazzmate.jazzmateshop.criticsReview.dto;

import lombok.Builder;
import lombok.Getter;
import shop.jazzmate.jazzmateshop.criticsReview.entity.CriticsReview;

import java.time.LocalDateTime;
import java.util.UUID;

@Getter
@Builder
public class CriticsReviewResponse {
    private UUID id;
    private String title;
    private String reviewer;
    private String reviewContent;
    private String reviewSummary;
    private String reviewUrl;
    private LocalDateTime createdAt;

    public static CriticsReviewResponse from(CriticsReview criticsReview) {
        return CriticsReviewResponse.builder()
                .id(criticsReview.getId())
                .title(criticsReview.getTitle())
                .reviewer(criticsReview.getReviewer())
                .reviewContent(criticsReview.getReviewContent())
                .reviewSummary(criticsReview.getReviewSummary())
                .reviewUrl(criticsReview.getReviewUrl())
                .createdAt(criticsReview.getCreatedAt())
                .build();
    }
}
