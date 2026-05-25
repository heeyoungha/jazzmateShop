package shop.jazzmate.jazzmateshop.recommendation.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class AiRecommendationClient {

    public void requestRecommendation(Integer reviewId, String reviewContent) {
        // TODO: FastAPI POST /recommend/by-review 호출
        // 실패 시 내부 catch — 감상문 저장 트랜잭션에 영향 없음
    }
}
