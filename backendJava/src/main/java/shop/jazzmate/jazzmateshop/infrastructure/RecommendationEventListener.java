package shop.jazzmate.jazzmateshop.infrastructure;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;
import shop.jazzmate.jazzmateshop.common.config.AsyncConfig;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.recommendation.client.AiRecommendationClient;
import shop.jazzmate.jazzmateshop.recommendation.event.RecommendationRequestEvent;
import shop.jazzmate.jazzmateshop.recommendation.event.ReviewEmbeddingSaveEvent;
import shop.jazzmate.jazzmateshop.userReview.UserReviewRepository;

@Component
@RequiredArgsConstructor
@Slf4j
public class RecommendationEventListener {

    private final AiRecommendationClient aiRecommendationClient;
    private final UserReviewRepository userReviewRepository;

    @Async(AsyncConfig.RECOMMENDATION_TASK_EXECUTOR)
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void requestRecommendation(RecommendationRequestEvent event) {
        aiRecommendationClient.requestRecommendation(
                event.reviewId(),
                event.reviewContent(),
                event.userId()
        );
    }

    @Async(AsyncConfig.RECOMMENDATION_TASK_EXECUTOR)
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void saveReviewEmbedding(ReviewEmbeddingSaveEvent event) {
        try {
            userReviewRepository.findById(event.reviewId()).ifPresentOrElse(
                review -> {
                    review.saveReviewEmbedding(event.embedding());
                    log.info("review_embedding 저장 완료: reviewId={}, dimensions={}", event.reviewId(), event.embedding().size());
                },
                () -> log.warn("review_embedding 저장 대상 없음: reviewId={}", event.reviewId())
            );
        } catch (Exception e) {
            log.error("review_embedding 저장 실패 (best-effort, 무시): reviewId={}", event.reviewId(), e);
        }
    }
}
