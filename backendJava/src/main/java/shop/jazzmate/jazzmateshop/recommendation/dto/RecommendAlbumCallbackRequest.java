package shop.jazzmate.jazzmateshop.recommendation.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendationStatus;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class RecommendAlbumCallbackRequest {

    @NotNull
    private RecommendationStatus status;
    @NotNull
    @Valid
    private List<Item> recommendations;
    private String errorCode;
    private String message;

    @AssertTrue(message = "COMPLETED callback requires at least one recommendation")
    public boolean isCompletedPayloadValid() {
        if (status != RecommendationStatus.COMPLETED) {
            return true;
        }
        return recommendations != null && !recommendations.isEmpty();
    }

    @AssertTrue(message = "FAILED callback requires errorCode/message and empty recommendations")
    public boolean isFailedPayloadValid() {
        if (status != RecommendationStatus.FAILED) {
            return true;
        }
        return isNotBlank(errorCode) && isNotBlank(message)
                && recommendations != null && recommendations.isEmpty();
    }

    private boolean isNotBlank(String value) {
        return value != null && !value.isBlank();
    }

    @Getter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Item {
        // v_embedding_with_album.album_id (= embedding_vectors.id)
        @NotBlank
        private String albumId;
        @NotBlank
        private String albumArtist;
        @NotBlank
        private String albumTitle;
        @NotNull
        private BigDecimal recommendationScore;
        @NotBlank
        private String recommendationReason;
        // v_review_summary.id (= allthatjazz_raw.id)
        @NotNull
        private UUID criticsReviewId;
    }
}
