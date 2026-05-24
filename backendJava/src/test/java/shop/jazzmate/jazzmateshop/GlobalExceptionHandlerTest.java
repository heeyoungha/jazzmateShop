package shop.jazzmate.jazzmateshop;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import shop.jazzmate.jazzmateshop.common.exception.GlobalExceptionHandler;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.userReview.UserReviewController;
import shop.jazzmate.jazzmateshop.userReview.UserReviewService;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;

import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(UserReviewController.class)
@Import(GlobalExceptionHandler.class)
class GlobalExceptionHandlerTest {

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper objectMapper;

    @MockBean
    UserReviewService userReviewService;
    @Test
    @DisplayName("@Valid 실패 → 400, success=false, message 존재")
    void validationError_returns400() throws Exception {
        String body = objectMapper.writeValueAsString(Map.of(
                "trackName", "",           // @NotBlank 위반
                "artistName", "Miles Davis",
                "reviewContent", "재즈의 정수"
        ));

        mockMvc.perform(post("/api/user-reviews")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").isNotEmpty());
    }

    @Test
    @DisplayName("ResourceNotFoundException → 404, success=false, message 포함")
    void resourceNotFound_returns404() throws Exception {
        given(userReviewService.getUserReview(999))
                .willThrow(new ResourceNotFoundException("감상문을 찾을 수 없습니다: 999"));

        mockMvc.perform(get("/api/user-reviews/999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").value("감상문을 찾을 수 없습니다: 999"));
    }

    @Test
    @DisplayName("RuntimeException → 500, success=false, 서버 오류 메시지")
    void unexpectedException_returns500() throws Exception {
        given(userReviewService.createUserReview(any(UserReviewRequest.class)))
                .willThrow(new RuntimeException("예상치 못한 오류"));

        String body = objectMapper.writeValueAsString(Map.of(
                "trackName", "So What",
                "artistName", "Miles Davis",
                "reviewContent", "재즈의 정수"
        ));

        mockMvc.perform(post("/api/user-reviews")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.message").value("서버 오류가 발생했습니다."));
    }
}
