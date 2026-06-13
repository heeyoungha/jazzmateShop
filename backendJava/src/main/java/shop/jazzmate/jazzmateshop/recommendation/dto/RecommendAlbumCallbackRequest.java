package shop.jazzmate.jazzmateshop.recommendation.dto;

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

    private RecommendationStatus status;
    private List<Item> recommendations;
    private String errorCode;
    private String message;

    @Getter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Item {
        // v_embedding_with_album.album_id (= embedding_vectors.id)
        private String albumId;
        private String albumArtist;
        private String albumTitle;
        private BigDecimal recommendationScore;
        private String recommendationReason;
        // v_review_summary.id (= allthatjazz_raw.id)
        private UUID criticsReviewId;
    }
}
