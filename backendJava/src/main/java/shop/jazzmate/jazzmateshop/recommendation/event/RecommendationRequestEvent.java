package shop.jazzmate.jazzmateshop.recommendation.event;

public record RecommendationRequestEvent(Integer reviewId, String reviewContent) {
}
