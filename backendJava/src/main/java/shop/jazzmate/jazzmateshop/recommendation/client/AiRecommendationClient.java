package shop.jazzmate.jazzmateshop.recommendation.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.net.http.HttpClient;
import java.util.Map;

@Component
@Slf4j
public class AiRecommendationClient {

    private final RestClient restClient;

    public AiRecommendationClient(@Value("${fastapi.base-url}") String fastapiBaseUrl) {
        HttpClient httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .build();
        this.restClient = RestClient.builder()
                .baseUrl(fastapiBaseUrl)
                .requestFactory(new JdkClientHttpRequestFactory(httpClient))
                .build();
    }

    public void requestRecommendation(Integer reviewId, String reviewContent) {
        try {
            ResponseEntity<Void> response = restClient.post()
                    .uri("/recommend/review")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of("review_id", reviewId, "review_content", reviewContent))
                    .retrieve()
                    .toBodilessEntity();
            log.info("FastAPI 추천 요청 전송 완료: reviewId={}, status={}", reviewId, response.getStatusCode());
        } catch (Exception e) {
            log.error("FastAPI 추천 요청 실패: reviewId={}, error={}", reviewId, e.getMessage(), e);
            throw new IllegalStateException("FastAPI recommendation request failed: reviewId=" + reviewId, e);
        }
    }
}
