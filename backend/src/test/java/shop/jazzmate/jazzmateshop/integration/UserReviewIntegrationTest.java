package shop.jazzmate.jazzmateshop.integration;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.transaction.annotation.Transactional;
import shop.jazzmate.jazzmateshop.userReview.RecommendTrackRepository;
import shop.jazzmate.jazzmateshop.userReview.TrackRepository;
import shop.jazzmate.jazzmateshop.userReview.UserReviewRepository;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendTrack;
import shop.jazzmate.jazzmateshop.userReview.entity.Track;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
@DisplayName("UserReview 통합테스트 - 전체 플로우 검증")
class UserReviewIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private UserReviewRepository userReviewRepository;

    @Autowired
    private RecommendTrackRepository recommendTrackRepository;

    @Autowired
    private TrackRepository trackRepository;

    // 공통 테스트 데이터 (각 테스트에서 재사용)
    private UserReviewRequest defaultRequest;

    // 각 테스트 전에 공통 테스트 데이터 준비
    @BeforeEach
    void setUp() {
        defaultRequest = createUserReviewRequest();
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

    private UserReview createUserReviewEntity() {
        return UserReview.builder()
            .trackName("Blue in Green")
            .artistName("Miles Davis")
            .reviewContent("Review content")
            .isPublic(true)
            .isFeatured(false)
            .likeCount(0)
            .commentCount(0)
            .build();
    }

    private Track createTrackEntity() {
        return Track.builder()
            .trackTitle("So What")
            .artistName("Miles Davis")
            .genre("Jazz")
            .build();
    }

    private RecommendTrack createRecommendTrack(Integer userReviewId, Integer trackId) {
        return RecommendTrack.builder()
            .userReviewId(userReviewId)
            .trackId(trackId)
            .recommendationScore(new BigDecimal("0.95"))
            .recommendationReason("유사한 재즈 스타일입니다.")
            .build();
    }

    @Test
    @DisplayName("감상문 생성 전체 플로우 - HTTP 요청부터 DB 저장까지")
    void testCreateUserReview_전체_플로우() throws Exception {
        // given
        // when - HTTP 요청
        mockMvc.perform(post("/api/user-reviews")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(defaultRequest)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.success").value(true))
            .andExpect(jsonPath("$.message").value("감상문이 성공적으로 저장되었습니다."))
            .andExpect(jsonPath("$.data.trackName").value("Blue in Green"))
            .andExpect(jsonPath("$.data.artistName").value("Miles Davis"))
            .andExpect(jsonPath("$.data.isFeatured").value(false))
            .andExpect(jsonPath("$.data.likeCount").value(0))
            .andExpect(jsonPath("$.data.commentCount").value(0));

        // then - 실제 DB에 저장되었는지 확인
        List<UserReview> savedReviews = userReviewRepository.findAll();
        assertThat(savedReviews).hasSize(1);
        
        UserReview savedReview = savedReviews.get(0);
        assertThat(savedReview.getTrackName()).isEqualTo("Blue in Green");
        assertThat(savedReview.getArtistName()).isEqualTo("Miles Davis");
        assertThat(savedReview.getReviewContent()).isEqualTo("이 곡은 정말 아름다운 재즈 곡입니다.");
        assertThat(savedReview.getRating()).isEqualByComparingTo(new BigDecimal("4.5"));
        assertThat(savedReview.getIsFeatured()).isFalse();
        assertThat(savedReview.getLikeCount()).isEqualTo(0);
        assertThat(savedReview.getCommentCount()).isEqualTo(0);
        assertThat(savedReview.getCreatedAt()).isNotNull();
        assertThat(savedReview.getUpdatedAt()).isNotNull();
        assertThat(savedReview.getMood()).isEqualTo("평온한");
        assertThat(savedReview.getGenre()).isEqualTo("Jazz");
        assertThat(savedReview.getIsPublic()).isTrue();
    }

    @Test
    @DisplayName("감상문 조회 - 추천 결과 포함")
    void testGetUserReview_추천_결과_포함() throws Exception {
        // given
        UserReview review = createUserReviewEntity();
        UserReview savedReview = userReviewRepository.save(review);

        Track track = createTrackEntity();
        Track savedTrack = trackRepository.save(track);

        RecommendTrack recommendTrack = createRecommendTrack(
            savedReview.getId(), 
            savedTrack.getId()
        );
        recommendTrackRepository.save(recommendTrack);

        // when & then
        mockMvc.perform(get("/api/user-reviews/{id}", savedReview.getId()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(savedReview.getId()))
            .andExpect(jsonPath("$.trackName").value("Blue in Green"))
            .andExpect(jsonPath("$.artistName").value("Miles Davis"))
            .andExpect(jsonPath("$.recommendations").isArray())
            .andExpect(jsonPath("$.recommendations").isNotEmpty())
            .andExpect(jsonPath("$.recommendations[0].trackId").value(savedTrack.getId()))
            .andExpect(jsonPath("$.recommendations[0].recommendationScore").value(0.95))
            .andExpect(jsonPath("$.hasRecommendations").value(true));

        // DB에서 추천 결과 확인
        List<RecommendTrack> savedRecommendations = recommendTrackRepository.findByUserReviewId(savedReview.getId());
        assertThat(savedRecommendations).hasSize(1);
        assertThat(savedRecommendations.get(0).getTrackId()).isEqualTo(savedTrack.getId());
        assertThat(savedRecommendations.get(0).getRecommendationScore()).isEqualByComparingTo(new BigDecimal("0.95"));
    }

    @Test
    @DisplayName("감상문 목록 조회 - 페이징 및 필터링")
    void testGetUserReviews_페이징_필터링() throws Exception {
        // given
        for (int i = 1; i <= 5; i++) {
            UserReview review = createUserReviewEntity();
            review.setTrackName("Track " + i);
            review.setArtistName("Artist " + i);
            review.setIsPublic(i <= 3);
            userReviewRepository.save(review);
        }

        // when & then - 공개 감상문만 조회 (userId 없음)
        mockMvc.perform(get("/api/user-reviews")
                .param("page", "0")
                .param("size", "10"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$.length()").value(3))
            .andExpect(jsonPath("$[0].isPublic").value(true))
            .andExpect(jsonPath("$[1].isPublic").value(true))
            .andExpect(jsonPath("$[2].isPublic").value(true));

        // when & then - 공개 감상문 조회 (모든 감상문)
        String response = mockMvc.perform(get("/api/user-reviews")
                .param("page", "0")
                .param("size", "10"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$.length()").value(3))
            .andReturn()
            .getResponse()
            .getContentAsString();

        // 공개 감상문만 조회되는지 검증
        List<UserReviewResponse> reviews = Arrays.asList(
            objectMapper.readValue(response, UserReviewResponse[].class)
        );
        assertThat(reviews).hasSize(3);
        // CreatedAtDesc로 정렬되므로 최신순(3, 2, 1)으로 반환됨
        assertThat(reviews).extracting("trackName")
            .containsExactly("Track 3", "Track 2", "Track 1");
        assertThat(reviews).extracting("isPublic").containsOnly(true);
        assertThat(reviews.get(0).getIsPublic()).isTrue();
        assertThat(reviews.get(2).getIsPublic()).isTrue();
    }

    @Test
    @DisplayName("감상문 수정 - DB 업데이트 검증")
    void testUpdateUserReview_DB_업데이트() throws Exception {
        // given
        UserReview review = createUserReviewEntity();
        UserReview savedReview = userReviewRepository.save(review);
        LocalDateTime originalCreatedAt = savedReview.getCreatedAt();

        UserReviewRequest updateRequest = UserReviewRequest.builder()
            .trackName("Updated Track")
            .artistName("Updated Artist")
            .reviewContent("Updated content")
            .rating(new BigDecimal("5.0"))
            .isPublic(false)
            .build();

        // when
        mockMvc.perform(put("/api/user-reviews/{id}", savedReview.getId())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(updateRequest)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.success").value(true))
            .andExpect(jsonPath("$.message").value("감상문이 성공적으로 수정되었습니다."))
            .andExpect(jsonPath("$.data.trackName").value("Updated Track"))
            .andExpect(jsonPath("$.data.artistName").value("Updated Artist"))
            .andExpect(jsonPath("$.data.isPublic").value(false));

        // then - DB에서 실제 업데이트 확인
        UserReview updatedReview = userReviewRepository.findById(savedReview.getId())
            .orElseThrow();
        assertThat(updatedReview.getTrackName()).isEqualTo("Updated Track");
        assertThat(updatedReview.getArtistName()).isEqualTo("Updated Artist");
        assertThat(updatedReview.getReviewContent()).isEqualTo("Updated content");
        assertThat(updatedReview.getRating()).isEqualByComparingTo(new BigDecimal("5.0"));
        assertThat(updatedReview.getIsPublic()).isFalse();
        assertThat(updatedReview.getCreatedAt()).isEqualTo(originalCreatedAt); // createdAt은 변경되지 않음
        assertThat(updatedReview.getUpdatedAt()).isNotNull(); // updatedAt은 업데이트됨
        assertThat(updatedReview.getUpdatedAt()).isAfter(originalCreatedAt);
        assertThat(updatedReview.getIsFeatured()).isFalse();
        assertThat(updatedReview.getLikeCount()).isEqualTo(0);
        assertThat(updatedReview.getCommentCount()).isEqualTo(0);
    }

    @Test
    @DisplayName("감상문 삭제 - DB 삭제 검증")
    void testDeleteUserReview_DB_삭제() throws Exception {
        // given
        UserReview review = createUserReviewEntity();
        UserReview savedReview = userReviewRepository.save(review);
        Integer reviewId = savedReview.getId();

        // 삭제 전 존재 확인
        assertThat(userReviewRepository.findById(reviewId)).isPresent();

        // when
        mockMvc.perform(delete("/api/user-reviews/{id}", reviewId))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.success").value(true))
            .andExpect(jsonPath("$.message").value("감상문이 성공적으로 삭제되었습니다."));

        // then - DB에서 실제 삭제 확인
        assertThat(userReviewRepository.findById(reviewId)).isEmpty();
    }

    @Test
    @DisplayName("추천 결과 조회 - HTTP 요청 검증")
    void testGetRecommendations_HTTP_요청() throws Exception {
        // given
        UserReview review = createUserReviewEntity();
        UserReview savedReview = userReviewRepository.save(review);

        Track track = createTrackEntity();
        Track savedTrack = trackRepository.save(track);

        RecommendTrack recommendTrack = createRecommendTrack(
            savedReview.getId(),
            savedTrack.getId()
        );
        recommendTrackRepository.save(recommendTrack);

        // when & then
        mockMvc.perform(get("/api/user-reviews/{id}/recommendations", savedReview.getId()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$").isNotEmpty())
            .andExpect(jsonPath("$[0].userReviewId").value(savedReview.getId()))
            .andExpect(jsonPath("$[0].trackId").value(savedTrack.getId()))
            .andExpect(jsonPath("$[0].recommendationScore").value(0.95))
            .andExpect(jsonPath("$[0].recommendationReason").value("유사한 재즈 스타일입니다."));

        // DB에서 추천 결과 확인
        List<RecommendTrack> savedRecommendations = recommendTrackRepository.findByUserReviewId(savedReview.getId());
        assertThat(savedRecommendations).hasSize(1);
        assertThat(savedRecommendations.get(0).getUserReviewId()).isEqualTo(savedReview.getId());
        assertThat(savedRecommendations.get(0).getTrackId()).isEqualTo(savedTrack.getId());
        assertThat(savedRecommendations.get(0).getRecommendationScore()).isEqualByComparingTo(new BigDecimal("0.95"));
        assertThat(savedRecommendations.get(0).getRecommendationReason()).isEqualTo("유사한 재즈 스타일입니다.");
    }

    @Test
    @DisplayName("추천 결과 조회 - 추천 결과가 없을 때 빈 배열 반환")
    void testGetRecommendations_EmptyResult() throws Exception {
        // given
        UserReview review = createUserReviewEntity();
        UserReview savedReview = userReviewRepository.save(review);

        // when & then
        mockMvc.perform(get("/api/user-reviews/{id}/recommendations", savedReview.getId()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray())
            .andExpect(jsonPath("$").isEmpty());

        // DB에서 추천 결과가 없는지 확인
        List<RecommendTrack> recommendations = recommendTrackRepository.findByUserReviewId(savedReview.getId());
        assertThat(recommendations).isEmpty();
    }
}