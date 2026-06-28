package shop.jazzmate.jazzmateshop.infrastructure;

import lombok.RequiredArgsConstructor;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;
import shop.jazzmate.jazzmateshop.common.config.AsyncConfig;
import shop.jazzmate.jazzmateshop.recommendation.client.AiRecommendationClient;
import shop.jazzmate.jazzmateshop.recommendation.event.RecommendationRequestEvent;

@Component
@RequiredArgsConstructor
public class RecommendationEventListener {

    private final AiRecommendationClient aiRecommendationClient;

    @Async(AsyncConfig.RECOMMENDATION_TASK_EXECUTOR)
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void requestRecommendation(RecommendationRequestEvent event) {
        aiRecommendationClient.requestRecommendation(
                event.reviewId(),
                event.reviewContent(),
                event.userId()
        );
    }
}
