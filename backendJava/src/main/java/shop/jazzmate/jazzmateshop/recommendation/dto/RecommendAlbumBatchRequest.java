package shop.jazzmate.jazzmateshop.recommendation.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class RecommendAlbumBatchRequest {

    private List<Item> recommendations;

    @Getter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Item {
        // v_album_embeddings.album_id (= embedding_vectors.id)
        private Integer albumId;
        private BigDecimal recommendationScore;
        private String recommendationReason;
    }
}
