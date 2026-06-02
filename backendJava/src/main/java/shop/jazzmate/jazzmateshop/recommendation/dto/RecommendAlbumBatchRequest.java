package shop.jazzmate.jazzmateshop.recommendation.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendationStatus;

import java.math.BigDecimal;
import java.util.List;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class RecommendAlbumBatchRequest {

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
        private BigDecimal recommendationScore;
        private String recommendationReason;
    }
}
