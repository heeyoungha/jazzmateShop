package shop.jazzmate.jazzmateshop.recommendation.dto;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendationStatus;

import static org.assertj.core.api.Assertions.assertThat;

class RecommendAlbumBatchRequestTest {

    private static final String ALBUM_ID = "00000000-0000-0000-0000-000000000101";
    private static final String FAILURE_ERROR_CODE = "NO_CANDIDATES";
    private static final String FAILURE_MESSAGE = "추천 후보가 없습니다.";

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Nested
    @DisplayName("JSON deserialization")
    class JsonDeserialization {

        @Test
        @DisplayName("COMPLETED 콜백 JSON → status와 recommendations 매핑")
        void completedCallbackJson_deserializesFields() throws Exception {
            String json = """
                    {
                      "status": "COMPLETED",
                      "recommendations": [
                        {
                          "albumId": "%s",
                          "recommendationScore": 0.9423,
                          "recommendationReason": "모달 재즈 특유의 정적인 분위기가 유사합니다."
                        }
                      ]
                    }
                    """.formatted(ALBUM_ID);

            RecommendAlbumBatchRequest request =
                    objectMapper.readValue(json, RecommendAlbumBatchRequest.class);

            assertThat(request.getStatus()).isEqualTo(RecommendationStatus.COMPLETED);
            assertThat(request.getRecommendations()).hasSize(1);
            assertThat(request.getRecommendations().get(0).getAlbumId()).isEqualTo(ALBUM_ID);
            assertThat(request.getRecommendations().get(0).getRecommendationScore()).isEqualByComparingTo("0.9423");
            assertThat(request.getRecommendations().get(0).getRecommendationReason())
                    .isEqualTo("모달 재즈 특유의 정적인 분위기가 유사합니다.");
            assertThat(request.getErrorCode()).isNull();
            assertThat(request.getMessage()).isNull();
        }

        @Test
        @DisplayName("FAILED 콜백 JSON → status와 errorCode/message 매핑")
        void failedCallbackJson_deserializesFields() throws Exception {
            String json = """
                    {
                      "status": "FAILED",
                      "recommendations": [],
                      "errorCode": "%s",
                      "message": "%s"
                    }
                    """.formatted(FAILURE_ERROR_CODE, FAILURE_MESSAGE);

            RecommendAlbumBatchRequest request =
                    objectMapper.readValue(json, RecommendAlbumBatchRequest.class);

            assertThat(request.getStatus()).isEqualTo(RecommendationStatus.FAILED);
            assertThat(request.getRecommendations()).isEmpty();
            assertThat(request.getErrorCode()).isEqualTo(FAILURE_ERROR_CODE);
            assertThat(request.getMessage()).isEqualTo(FAILURE_MESSAGE);
        }
    }
}
