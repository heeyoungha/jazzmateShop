package shop.jazzmate.jazzmateshop.userReview;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendTrack;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import org.springframework.test.context.TestPropertySource;

@WebMvcTest(UserReviewController.class)
@TestPropertySource(properties = {
    "server.port=8080",
    "SERVER_PORT=8080",
    "DB_URL=jdbc:h2:mem:testdb",
    "DB_USERNAME=sa",
    "DB_PASSWORD=",
    "DB_DRIVER=org.h2.Driver"
})
@DisplayName("UserReviewController 단위테스트")
class UserReviewControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockitoBean
    private UserReviewService userReviewService;

    // 공통 테스트 데이터 (각 테스트에서 재사용)
    private UserReviewRequest defaultRequest;
    private UserReviewResponse defaultResponse;

    // 각 테스트 전에 mock 초기화 및 공통 테스트 데이터 준비
    @BeforeEach
    void setUp() {
        reset(userReviewService);
        // 공통으로 사용되는 기본 테스트 데이터 준비
        defaultRequest = createUserReviewRequest();
        defaultResponse = createUserReviewResponse(1);
    }

    // 테스트 데이터 생성 헬퍼 메서드
    private UserReviewRequest createUserReviewRequest() {
        return UserReviewRequest.builder()
            .trackName("Blue in Green")
            .artistName("Miles Davis")
            .reviewContent("이 곡은 정말 아름다운 재즈 곡입니다.")
            .rating(new BigDecimal("4.5"))
            .mood("평온한")
            .genre("Jazz")
            .isPublic(true)
            .build();
    }

    private UserReviewResponse createUserReviewResponse(Integer id) {
        return UserReviewResponse.builder()
            .id(id)
            .trackName("Blue in Green")
            .artistName("Miles Davis")
            .reviewContent("이 곡은 정말 아름다운 재즈 곡입니다.")
            .rating(new BigDecimal("4.5"))
            .mood("평온한")
            .genre("Jazz")
            .isPublic(true)
            .isFeatured(false)
            .likeCount(0)
            .commentCount(0)
            .createdAt(LocalDateTime.now())
            .build();
    }


    /**
     * HTTP 레이어 테스트 - 감상문 생성 성공
     * 목적: POST 요청이 올바른 HTTP 상태 코드(200)와 응답 구조를 반환하는지 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직 - HTTP 인터페이스)
     */
    @Test
    @DisplayName("POST /api/user-reviews - 성공 시 200 OK 반환")
    @Tag("fast")
    void createUserReview_Success_ReturnsOk() throws Exception {
        // given
        when(userReviewService.createUserReview(any(UserReviewRequest.class)))
            .thenReturn(defaultResponse);

        // when & then - 핵심 필드만 검증 (행동 중심 테스트)
        mockMvc.perform(post("/api/user-reviews")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(defaultRequest)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.success").value(true))
            .andExpect(jsonPath("$.message").value("감상문이 성공적으로 저장되었습니다."))
            .andExpect(jsonPath("$.data.id").value(1))
            .andExpect(jsonPath("$.data.trackName").value("Blue in Green"));
        
        // Service 호출 검증 - Controller가 실제로 일을 했는지 확인
        verify(userReviewService, times(1))
            .createUserReview(any(UserReviewRequest.class));
    }

    /**
     * 예외 처리 테스트 - 유효성 검증 실패 (@Valid)
     * 목적: 필수 필드가 누락된 요청 시 @Valid 검증으로 400 Bad Request를 반환하는지 검증
     * 우선순위: 🥈 2단계 (에러/예외 처리 로직)
     * 
     * 가이드 적용: DTO에서 @Valid로 검증하므로 서비스 레이어에 도달하기 전에 검증 실패
     */
    @Test
    @DisplayName("POST /api/user-reviews - 필수값 누락 시 @Valid 검증으로 400 Bad Request 반환")
    void createUserReview_ValidationFails_Returns400() throws Exception {
        // given - 필수 필드 누락 (trackName, artistName, reviewContent)
        UserReviewRequest request = UserReviewRequest.builder()
            .trackName("")  // 빈 문자열
            .artistName(null)  // null
            // reviewContent 누락
            .isPublic(true)
            .build();

        // when & then - @Valid 검증 실패 시 400 Bad Request 반환
        // 서비스 레이어에 도달하기 전에 검증 실패하므로 서비스 mock 불필요
        mockMvc.perform(post("/api/user-reviews")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isBadRequest());
    }

    /**
     * 예외 처리 테스트 - 서비스 예외 발생
     * 목적: 서비스에서 예외 발생 시 GlobalExceptionHandler가 500 Internal Server Error를 반환하는지 검증
     * 우선순위: 🥈 2단계 (에러/예외 처리 로직)
     */
    @Test
    @DisplayName("서비스 예외 발생 시 GlobalExceptionHandler가 500 Internal Server Error 반환 (대표 케이스)")
    void serviceException_Returns500() throws Exception {
        // given - 어떤 API든 상관없이 서비스 예외 발생
        String errorMessage = "데이터베이스 연결 실패";

        when(userReviewService.createUserReview(any(UserReviewRequest.class)))
            .thenThrow(new RuntimeException(errorMessage));

        // when & then - GlobalExceptionHandler가 500 반환
        mockMvc.perform(post("/api/user-reviews")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(defaultRequest)))
            .andExpect(status().isInternalServerError())
            .andExpect(jsonPath("$.success").value(false))
            .andExpect(jsonPath("$.message").value("서버 내부 오류가 발생했습니다."));
        
        // Service 호출 검증 - 예외가 발생하기 전에 Service가 호출되었는지 확인
        verify(userReviewService, times(1))
            .createUserReview(any(UserReviewRequest.class));
    }

    /**
     * HTTP 레이어 테스트 - 페이징 파라미터 처리
     * 목적: 쿼리 파라미터(page, size)가 올바르게 파싱되고 서비스로 전달되는지 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직 - HTTP 인터페이스)
     */
    @Test
    @DisplayName("GET /api/user-reviews - 페이징 파라미터 전달")
    void getUserReviews_PassesPagingParameters() throws Exception {
        // given
        int page = 0;
        int size = 20;
        UserReviewResponse review = createUserReviewResponse(1);

        when(userReviewService.getUserReviews(isNull(), eq(page), eq(size)))
            .thenReturn(Arrays.asList(review));

        // when
        String response = mockMvc.perform(get("/api/user-reviews")
                .param("page", String.valueOf(page))
                .param("size", String.valueOf(size)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andReturn()
            .getResponse()
            .getContentAsString();

        // then - 핵심 필드만 검증 (행동 중심 테스트)
        List<UserReviewResponse> reviews = Arrays.asList(
            objectMapper.readValue(response, UserReviewResponse[].class)
        );
        assertThat(reviews).hasSize(1);
        assertThat(reviews.get(0).getId()).isEqualTo(1);
        
        // Service 호출 검증 - Controller가 실제로 일을 했는지 확인
        verify(userReviewService, times(1))
            .getUserReviews(isNull(), eq(page), eq(size));
    }
    
    /**
     * HTTP 레이어 테스트 - 감상문 목록 조회 (userId 파라미터 유무에 따른 분기)
     * 목적: userId 파라미터 유무에 따라 공개 감상문 또는 특정 사용자 감상문을 반환하는지 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직 - HTTP 인터페이스)
     * 
     * 가이드 적용: 같은 API의 분기 로직은 하나의 테스트에서 검증
     */
    @Test
    @DisplayName("GET /api/user-reviews - userId 파라미터 유무에 따른 분기 검증")
    void getUserReviews_WithAndWithoutUserId_ReturnsCorrectReviews() throws Exception {
        int page = 0;
        int size = 20;
        
        // 시나리오 1: userId 없을 때 - 공개 감상문 조회
        when(userReviewService.getUserReviews(isNull(), eq(page), eq(size)))
            .thenReturn(Collections.emptyList());

        mockMvc.perform(get("/api/user-reviews")
                .param("page", String.valueOf(page))
                .param("size", String.valueOf(size)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$").isEmpty());
        
        // 시나리오 2: userId 있을 때 - 특정 사용자 감상문 조회
        String userId = "user123";
        UserReviewResponse review = createUserReviewResponse(1);
        when(userReviewService.getUserReviews(eq(userId), eq(page), eq(size)))
            .thenReturn(Arrays.asList(review));

        mockMvc.perform(get("/api/user-reviews")
                .param("userId", userId)
                .param("page", String.valueOf(page))
                .param("size", String.valueOf(size)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].id").value(1))
            .andExpect(jsonPath("$[0].trackName").value("Track 1"));
        
        // Service 호출 검증 - 두 시나리오 모두 Service가 호출되었는지 확인
        verify(userReviewService, times(1))
            .getUserReviews(isNull(), eq(page), eq(size));
        verify(userReviewService, times(1))
            .getUserReviews(eq(userId), eq(page), eq(size));
    }

    /**
     * HTTP 레이어 테스트 - 감상문 조회 성공
     * 목적: 특정 감상문 조회 시 올바른 HTTP 상태 코드(200)와 응답 데이터를 반환하는지 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직 - HTTP 인터페이스)
     */
    @Test
    @DisplayName("GET /api/user-reviews/{id} - 200 OK 반환")
    void getUserReview_ReturnsOk() throws Exception {
        // given
        Integer reviewId = 1;
        List<RecommendTrack> recommendations = Collections.emptyList();

        // mock 동작 설정
        when(userReviewService.getUserReview(reviewId)).thenReturn(defaultResponse);
        when(userReviewService.getRecommendationsByReviewId(reviewId))
            .thenReturn(recommendations);

        // when & then - 핵심 필드만 검증 (행동 중심 테스트)
        mockMvc.perform(get("/api/user-reviews/{id}", reviewId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(reviewId))
            .andExpect(jsonPath("$.trackName").value("Blue in Green"));
        
        // Service 호출 검증 - Controller가 실제로 일을 했는지 확인
        verify(userReviewService, times(1)).getUserReview(reviewId);
        verify(userReviewService, times(1)).getRecommendationsByReviewId(reviewId);
    }

    /**
     * 예외 처리 테스트 - 리소스 없음 (대표 케이스)
     * 목적: 존재하지 않는 리소스 조회 시 GlobalExceptionHandler가 404 상태 코드를 반환하는지 검증
     * 우선순위: 🥈 2단계 (에러/예외 처리 로직)
     */
    @Test
    @DisplayName("리소스 없음 시 GlobalExceptionHandler가 404 Not Found 반환 (대표 케이스)")
    void resourceNotFound_Returns404() throws Exception {
        // given - 어떤 API든 상관없이 리소스 없음 예외 발생
        Integer reviewId = 999;
        when(userReviewService.getUserReview(reviewId))
            .thenThrow(new ResourceNotFoundException("감상문을 찾을 수 없습니다"));

        // when & then - GlobalExceptionHandler가 404 반환
        mockMvc.perform(get("/api/user-reviews/{id}", reviewId))
            .andExpect(status().isNotFound())
            .andExpect(jsonPath("$.success").value(false))
            .andExpect(jsonPath("$.message").value("감상문을 찾을 수 없습니다"));
        
        // Service 호출 검증 - 예외가 발생하기 전에 Service가 호출되었는지 확인
        verify(userReviewService, times(1)).getUserReview(reviewId);
    }

    /**
     * HTTP 레이어 테스트 - 감상문 수정 성공
     * 목적: PUT 요청이 올바른 HTTP 상태 코드(200)와 수정된 데이터를 반환하는지 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직 - HTTP 인터페이스)
     */
    @Test
    @DisplayName("PUT /api/user-reviews/{id} - 200 OK 반환")
    void updateUserReview_ReturnsOk() throws Exception {
        // given
        Integer reviewId = 1;
        UserReviewRequest request = UserReviewRequest.builder()
            .trackName("Updated Track")
            .artistName("Updated Artist")
            .reviewContent("Updated content")
            .rating(new BigDecimal("5.0"))
            .isPublic(false)
            .build();

        UserReviewResponse response = UserReviewResponse.builder()
            .id(reviewId)
            .trackName("Updated Track")
            .artistName("Updated Artist")
            .reviewContent("Updated content")
            .rating(new BigDecimal("5.0"))
            .isPublic(false)
            .isFeatured(false)
            .likeCount(0)
            .commentCount(0)
            .createdAt(LocalDateTime.now())
            .updatedAt(LocalDateTime.now())
            .build();

        when(userReviewService.updateUserReview(eq(reviewId), any(UserReviewRequest.class)))
            .thenReturn(response);

        // when & then - 핵심 필드만 검증 (행동 중심 테스트)
        mockMvc.perform(put("/api/user-reviews/{id}", reviewId)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.success").value(true))
            .andExpect(jsonPath("$.message").value("감상문이 성공적으로 수정되었습니다."))
            .andExpect(jsonPath("$.data.id").value(reviewId))
            .andExpect(jsonPath("$.data.trackName").value("Updated Track"));
        
        // Service 호출 검증 - Controller가 실제로 일을 했는지 확인
        verify(userReviewService, times(1))
            .updateUserReview(eq(reviewId), any(UserReviewRequest.class));
    }

    /**
     * HTTP 레이어 테스트 - 감상문 삭제 성공
     * 목적: DELETE 요청이 올바른 HTTP 상태 코드(200)와 성공 메시지를 반환하는지 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직 - HTTP 인터페이스)
     */
    @Test
    @DisplayName("DELETE /api/user-reviews/{id} - 200 OK 반환")
    void deleteUserReview_ReturnsOk() throws Exception {
        // given
        Integer reviewId = 1;
        doNothing().when(userReviewService).deleteUserReview(reviewId);

        // when & then
        mockMvc.perform(delete("/api/user-reviews/{id}", reviewId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.success").value(true))
            .andExpect(jsonPath("$.message").value("감상문이 성공적으로 삭제되었습니다."))
            .andExpect(jsonPath("$.data").doesNotExist());
        
        // Service 호출 검증 - Controller가 실제로 일을 했는지 확인
        verify(userReviewService, times(1)).deleteUserReview(reviewId);
    }

    /**
     * HTTP 레이어 테스트 - 추천 결과 조회 성공
     * 목적: 추천 결과 조회 API가 올바른 HTTP 상태 코드(200)와 추천 데이터를 반환하는지 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직 - HTTP 인터페이스)
     */
    @Test
    @DisplayName("GET /api/user-reviews/{id}/recommendations - 추천 결과 조회 성공")
    void getRecommendations_Success_ReturnsOk() throws Exception {
        // given
        Integer reviewId = 1;
        List<RecommendTrack> recommendations = Arrays.asList(
            RecommendTrack.builder()
                .id(1)
                .userReviewId(reviewId)
                .trackId(100)
                .recommendationScore(new BigDecimal("0.95"))
                .recommendationReason("유사한 재즈 스타일입니다.")
                .build()
        );

        when(userReviewService.getRecommendationsByReviewId(reviewId))
            .thenReturn(recommendations);

        // when & then
        mockMvc.perform(get("/api/user-reviews/{id}/recommendations", reviewId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$[0].userReviewId").value(reviewId))
            .andExpect(jsonPath("$[0].trackId").value(100))
            .andExpect(jsonPath("$[0].recommendationScore").value(0.95));
        
        // Service 호출 검증 - Controller가 실제로 일을 했는지 확인
        verify(userReviewService, times(1)).getRecommendationsByReviewId(reviewId);
    }

}