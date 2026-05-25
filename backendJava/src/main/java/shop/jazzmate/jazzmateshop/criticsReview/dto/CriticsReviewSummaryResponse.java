package shop.jazzmate.jazzmateshop.criticsReview.dto;

import lombok.Builder;
import lombok.Getter;
import shop.jazzmate.jazzmateshop.criticsReview.entity.CriticsReview;

import java.util.UUID;

@Getter
@Builder
public class CriticsReviewSummaryResponse {
    private UUID id;
    private String title;
    private String reviewer;
    private String reviewSummary;

    public static CriticsReviewSummaryResponse from(CriticsReview criticsReview) {
        return CriticsReviewSummaryResponse.builder()
                .id(criticsReview.getId())
                .title(criticsReview.getTitle())
                .reviewer(criticsReview.getReviewer())
                .reviewSummary(criticsReview.getReviewSummary())
                .build();
    }
}
