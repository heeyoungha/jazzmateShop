package shop.jazzmate.jazzmateshop.recommendation;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import shop.jazzmate.jazzmateshop.common.exception.GlobalExceptionHandler;
import shop.jazzmate.jazzmateshop.recommendation.dto.RecommendAlbumBatchRequest;

import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(RecommendAlbumController.class)
@Import(GlobalExceptionHandler.class)
class RecommendAlbumControllerTest {

    private static final int REVIEW_ID = 42;

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper objectMapper;

    @MockBean
    RecommendAlbumService recommendAlbumService;

    @Nested
    @DisplayName("POST /api/user-reviews/{reviewId}/recommendations")
    class CreateRecommendations {

        @Test
        @DisplayName("COMPLETED 콜백 → HTTP 200, 빈 body, service 호출")
        void createRecommendations_completedCallback_returns200AndDelegates() throws Exception {
            mockMvc.perform(post("/api/user-reviews/{reviewId}/recommendations", REVIEW_ID)
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(Map.of(
                                    "status", "COMPLETED",
                                    "recommendations", java.util.List.of()
                            ))))
                    .andExpect(status().isOk())
                    .andExpect(content().string(""));

            verify(recommendAlbumService).createRecommendAlbums(eq(REVIEW_ID), any(RecommendAlbumBatchRequest.class));
        }

        @Test
        @DisplayName("FAILED 콜백 → HTTP 200, 빈 body, service 호출")
        void createRecommendations_failedCallback_returns200AndDelegates() throws Exception {
            mockMvc.perform(post("/api/user-reviews/{reviewId}/recommendations", REVIEW_ID)
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(Map.of(
                                    "status", "FAILED",
                                    "recommendations", java.util.List.of(),
                                    "errorCode", "NO_CANDIDATES",
                                    "message", "추천 후보가 없습니다."
                            ))))
                    .andExpect(status().isOk())
                    .andExpect(content().string(""));

            verify(recommendAlbumService).createRecommendAlbums(eq(REVIEW_ID), any(RecommendAlbumBatchRequest.class));
        }
    }
}
