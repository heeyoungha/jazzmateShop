package shop.jazzmate.jazzmateshop.recommendation.event;

import java.util.List;

public record ReviewEmbeddingSaveEvent(Integer reviewId, List<Float> embedding) {
}
