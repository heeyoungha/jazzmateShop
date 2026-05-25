package shop.jazzmate.jazzmateshop.criticsReview;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;
import shop.jazzmate.jazzmateshop.common.exception.GlobalExceptionHandler;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.criticsReview.entity.CriticsReview;

import java.util.UUID;

import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(CriticsReviewController.class)
@Import(GlobalExceptionHandler.class)
class CriticsReviewControllerTest {

    @Autowired
    MockMvc mockMvc;

    @MockBean
    CriticsReviewService criticsReviewService;

    private static final UUID DEFAULT_ID = UUID.fromString("00000000-0000-0000-0000-000000000001");

    private final CriticsReview DEFAULT_REVIEW = CriticsReview.builder()
            .id(DEFAULT_ID)
            .title("Kind of Blue")
            .reviewer("AllAboutJazz")
            .reviewSummary("GPT 요약 내용")
            .reviewContent("원문 내용")
            .reviewUrl("https://example.com")
            .build();

    // ────────────────────────────────────────────────
    // GET /api/critics/{id}
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("GET /api/critics/{id}")
    class GetReview {

        @Test
        @DisplayName("존재하는 id → HTTP 200")
        void getReview_existingId_returnsDetailResponse() throws Exception {
            given(criticsReviewService.getReview(DEFAULT_ID)).willReturn(DEFAULT_REVIEW);

            mockMvc.perform(get("/api/critics/" + DEFAULT_ID))
                    .andExpect(status().isOk());
        }

        @Test
        @DisplayName("존재하지 않는 id → HTTP 404, success=false")
        void getReview_notFound_returns404() throws Exception {
            given(criticsReviewService.getReview(DEFAULT_ID))
                    .willThrow(new ResourceNotFoundException("CriticsReview not found: " + DEFAULT_ID));

            mockMvc.perform(get("/api/critics/" + DEFAULT_ID))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.success").value(false));
        }
    }
}
