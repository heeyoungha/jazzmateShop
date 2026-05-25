package shop.jazzmate.jazzmateshop.userReview;

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
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewCreateResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.util.Map;

import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * UserReviewController 슬라이스 테스트
 *
 * 검증 범위: 예외 경로만 (@Valid → 400, ResourceNotFoundException → 404)
 * 성공 경로(200)는 Playwright E2E 테스트에서 검증
 */
@WebMvcTest(UserReviewController.class)
@Import(GlobalExceptionHandler.class)
class UserReviewControllerTest {

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper objectMapper;

    @MockBean
    UserReviewService userReviewService;

    private static final int DEFAULT_ID = 1;

    // ────────────────────────────────────────────────
    // POST /api/user-reviews
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("POST /api/user-reviews")
    class CreateUserReview {

        @Test
        @DisplayName("저장 성공 → HTTP 201, success=true, data.id 포함")
        void create_success_returns201WithDataId() throws Exception {
            UserReviewCreateResponse response = UserReviewCreateResponse.from(UserReview.builder().id(DEFAULT_ID).build());
            given(userReviewService.createUserReview(org.mockito.ArgumentMatchers.any(UserReviewRequest.class)))
                    .willReturn(response);

            mockMvc.perform(post("/api/user-reviews")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(Map.of(
                                    "trackName", "So What",
                                    "artistName", "Miles Davis",
                                    "reviewContent", "재즈의 정수"
                            ))))
                    .andExpect(status().isCreated())
                    .andExpect(jsonPath("$.success").value(true))
                    .andExpect(jsonPath("$.message").value("감상문이 저장되었습니다."))
                    .andExpect(jsonPath("$.data.id").value(DEFAULT_ID));
        }

        @Test
        @DisplayName("trackName 누락 → HTTP 400, success=false")
        void create_missingTrackName_returns400() throws Exception {
            mockMvc.perform(post("/api/user-reviews")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(Map.of(
                                    "artistName", "Miles Davis",
                                    "reviewContent", "재즈의 정수"
                            ))))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.success").value(false));
        }

        @Test
        @DisplayName("artistName 누락 → HTTP 400, success=false")
        void create_missingArtistName_returns400() throws Exception {
            mockMvc.perform(post("/api/user-reviews")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(Map.of(
                                    "trackName", "So What",
                                    "reviewContent", "재즈의 정수"
                            ))))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.success").value(false));
        }

        @Test
        @DisplayName("reviewContent 누락 → HTTP 400, success=false")
        void create_missingReviewContent_returns400() throws Exception {
            mockMvc.perform(post("/api/user-reviews")
                            .contentType(MediaType.APPLICATION_JSON)
                            .content(objectMapper.writeValueAsString(Map.of(
                                    "trackName", "So What",
                                    "artistName", "Miles Davis"
                            ))))
                    .andExpect(status().isBadRequest())
                    .andExpect(jsonPath("$.success").value(false));
        }

    }

    // ────────────────────────────────────────────────
    // GET /api/user-reviews/{id}
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("GET /api/user-reviews/{id}")
    class GetUserReview {

        @Test
        @DisplayName("존재하지 않는 id → HTTP 404, success=false")
        void getById_notFound_returns404() throws Exception {
            given(userReviewService.getUserReview(DEFAULT_ID))
                    .willThrow(new ResourceNotFoundException("UserReview not found: " + DEFAULT_ID));

            mockMvc.perform(get("/api/user-reviews/" + DEFAULT_ID))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.success").value(false));
        }
    }

    // ────────────────────────────────────────────────
    // POST /api/user-reviews/{id}/retry
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("POST /api/user-reviews/{id}/retry")
    class RetryRecommendation {

        @Test
        @DisplayName("재시도 성공 → HTTP 200, success=true, data=null")
        void retry_success_returnsApiResponse() throws Exception {
            mockMvc.perform(post("/api/user-reviews/1/retry"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.success").value(true))
                    .andExpect(jsonPath("$.message").value("추천 재시도를 시작했습니다."))
                    .andExpect(jsonPath("$.data").doesNotExist());
        }

        @Test
        @DisplayName("존재하지 않는 id → HTTP 404, success=false")
        void retry_notFound_returns404() throws Exception {
            doThrow(new ResourceNotFoundException("UserReview not found: " + DEFAULT_ID))
                    .when(userReviewService).retryRecommendation(DEFAULT_ID);

            mockMvc.perform(post("/api/user-reviews/" + DEFAULT_ID + "/retry"))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.success").value(false));
        }
    }

}
