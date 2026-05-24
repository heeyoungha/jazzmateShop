package shop.jazzmate.jazzmateshop.infrastructure;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import shop.jazzmate.jazzmateshop.recommendation.client.AiRecommendationClient;
import shop.jazzmate.jazzmateshop.recommendation.event.RecommendationRequestEvent;

import static org.mockito.Mockito.*;

/**
 * NOTE: @TransactionalEventListener / @Async는 Spring 컨텍스트 없이는 직접 트리거할 수 없으므로
 *       메서드를 직접 호출하여 위임 로직만 검증한다.
 *       AFTER_COMMIT + @Async 동작은 통합 테스트(RecommendationFlowIntegrationTest)에서 검증한다.
 *
 */
@ExtendWith(MockitoExtension.class)
class RecommendationEventListenerTest {

    @Mock
    AiRecommendationClient aiRecommendationClient;

    @InjectMocks
    RecommendationEventListener recommendationEventListener;

    @Nested
    @DisplayName("requestRecommendation — AI 클라이언트 위임")
    class RequestRecommendation {

        @Test
        @DisplayName("AiRecommendationClient.requestRecommendation 정확한 파라미터로 호출")
        void requestRecommendation_delegatesToClient() {
            RecommendationRequestEvent event =
                    new RecommendationRequestEvent(42, "명반 중의 명반, 재즈의 정수");

            recommendationEventListener.requestRecommendation(event);

            verify(aiRecommendationClient, times(1))
                    .requestRecommendation(42, "명반 중의 명반, 재즈의 정수");
        }
    }
}
