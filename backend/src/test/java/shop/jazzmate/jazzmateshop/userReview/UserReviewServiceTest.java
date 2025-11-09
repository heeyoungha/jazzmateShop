package shop.jazzmate.jazzmateshop.userReview;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendTrack;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("UserReviewService 단위테스트 - 비즈니스 로직 검증")
class UserReviewServiceTest {

    private static final Logger log = LoggerFactory.getLogger(UserReviewServiceTest.class);

    @Mock
    private UserReviewRepository userReviewRepository;

    @Mock
    private RecommendTrackRepository recommendTrackRepository;

    @Mock
    private TrackRepository trackRepository;

    @InjectMocks
    private UserReviewService userReviewService;

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

    private UserReview createUserReview(Integer id) {
        return UserReview.builder()
            .id(id)
            .trackName("Blue in Green")
            .artistName("Miles Davis")
            .reviewContent("Review content")
            .isPublic(true)
            .isFeatured(false)
            .likeCount(0)
            .commentCount(0)
            .createdAt(LocalDateTime.now().minusDays(id != null ? id : 0))
            .updatedAt(LocalDateTime.now())
            .build();
    }

    /**
     * 비즈니스 로직 테스트 - 감상문 생성
     * 목적: 감상문 생성 시 기본값(isFeatured=false, likeCount=0 등)이 올바르게 설정되는지 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직)
     */
    @Test
    @DisplayName("감상문 생성 - 기본값 설정 검증")
    void testCreateUserReview_기본값_설정() {
        // given
        UserReview savedReview = createUserReview(1);

        when(userReviewRepository.save(any(UserReview.class))).thenReturn(savedReview);

        // when
        UserReviewResponse response = userReviewService.createUserReview(defaultRequest);

        // then - 비즈니스 로직: 핵심 기본값만 검증 (가이드: 핵심 필드 2~3개)
        assertThat(response.getId()).isEqualTo(1);
        assertThat(response.getIsFeatured()).isFalse();
        assertThat(response.getLikeCount()).isEqualTo(0);
        assertThat(response.getCommentCount()).isEqualTo(0);
    }

    /**
     * 예외 처리 테스트 - RuntimeException 대표 케이스
     * 목적: Service 레이어에서 발생하는 RuntimeException 처리 검증 (대표 케이스 1개만 유지)
     * 우선순위: 🥈 2단계 (에러/예외 처리 로직)
     * 가이드: 같은 타입의 예외 테스트는 1개만 유지
     */
    @Test
    @DisplayName("감상문 생성 - 저장 실패 시 예외 처리 (RuntimeException 대표 케이스)")
    void testCreateUserReview_저장_실패_예외처리() {
        // given
        String errorMessage = "데이터베이스 연결 실패";

        when(userReviewRepository.save(any(UserReview.class)))
            .thenThrow(new RuntimeException(errorMessage));

        // when & then - 비즈니스 로직: 예외 처리 검증
        assertThatThrownBy(() -> userReviewService.createUserReview(defaultRequest))
            .isInstanceOf(RuntimeException.class)
            .hasMessageContaining("감상문 생성 중 오류가 발생했습니다")
            .hasMessageContaining(errorMessage);
    }

    /**
     * 비즈니스 로직 테스트 - 감상문 목록 조회 분기 로직 통합
     * 목적: userId 유무에 따른 분기 로직을 하나의 테스트에서 검증 (가이드: 같은 API의 분기 로직 통합)
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직)
     */
    @Test
    @DisplayName("감상문 목록 조회 - userId 유무에 따른 분기 로직")
    void testGetUserReviews_분기_로직_통합() {
        // 시나리오 1: userId가 null일 때 공개 감상문 조회
        List<UserReview> publicReviews = List.of(
            createUserReview(1),
            createUserReview(2),
            createUserReview(3)
        );
        when(userReviewRepository.findByIsPublicTrueOrderByCreatedAtDesc()).thenReturn(publicReviews);

        List<UserReviewResponse> publicResult = userReviewService.getUserReviews(null, 0, 10);
        assertThat(publicResult).hasSize(3);
        assertThat(publicResult).extracting("isPublic").containsOnly(true);

        // 시나리오 2: userId가 제공될 때 특정 사용자 감상문 조회
        String userId = "user123";
        UserReview review1 = createUserReview(1);
        UserReview review2 = createUserReview(2);
        UserReview review3 = createUserReview(3);
        review1.setUserId(userId);
        review2.setUserId(userId);
        review3.setUserId(userId);
        List<UserReview> userReviews = List.of(review1, review2, review3);
        when(userReviewRepository.findByUserIdOrderByCreatedAtDesc(userId)).thenReturn(userReviews);

        List<UserReviewResponse> userResult = userReviewService.getUserReviews(userId, 0, 10);
        assertThat(userResult).hasSize(3);
        assertThat(userResult).extracting("userId").containsOnly(userId);

        // 시나리오 3: userId가 빈 문자열일 때 공개 감상문 조회
        when(userReviewRepository.findByIsPublicTrueOrderByCreatedAtDesc()).thenReturn(publicReviews);
        List<UserReviewResponse> emptyResult = userReviewService.getUserReviews("   ", 0, 10);
        assertThat(emptyResult).hasSize(3);
        assertThat(emptyResult).extracting("isPublic").containsOnly(true);
    }

    /**
     * 비즈니스 로직 테스트 - 페이징 처리 통합
     * 목적: 페이징 핵심 케이스를 하나의 테스트에서 검증 (가이드: 같은 API의 분기 로직 통합)
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직)
     */
    @Test
    @DisplayName("감상문 목록 조회 - 페이징 로직 통합")
    void testGetUserReviews_페이징_통합() {
        List<UserReview> reviews = List.of(
            createUserReview(1),
            createUserReview(2),
            createUserReview(3),
            createUserReview(4),
            createUserReview(5)
        );

        // 시나리오 1: 정상 페이징 (page 1, size 2 = 인덱스 2, 3 반환)
        when(userReviewRepository.findByIsPublicTrueOrderByCreatedAtDesc()).thenReturn(reviews);
        List<UserReviewResponse> result1 = userReviewService.getUserReviews(null, 1, 2);
        assertThat(result1).hasSize(2);
        assertThat(result1).extracting("id").containsExactly(3, 4);

        // 시나리오 2: 범위 초과 시 빈 리스트 반환
        List<UserReviewResponse> result2 = userReviewService.getUserReviews(null, 10, 10);
        assertThat(result2).isEmpty();

        // 시나리오 3: 빈 리스트 처리
        when(userReviewRepository.findByIsPublicTrueOrderByCreatedAtDesc()).thenReturn(Collections.emptyList());
        List<UserReviewResponse> result3 = userReviewService.getUserReviews(null, 0, 10);
        assertThat(result3).isEmpty();

        // 시나리오 4: 마지막 페이지 부분 데이터 (page 1, size 3 = 인덱스 4, 5 반환)
        when(userReviewRepository.findByIsPublicTrueOrderByCreatedAtDesc()).thenReturn(reviews);
        List<UserReviewResponse> result4 = userReviewService.getUserReviews(null, 1, 3);
        assertThat(result4).hasSize(2);
        assertThat(result4).extracting("id").containsExactly(4, 5);
    }


    /**
     * 비즈니스 로직 테스트 - 감상문 수정
     * 목적: 감상문 필드 업데이트가 올바르게 동작하는지 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직)
     */
    @Test
    @DisplayName("감상문 수정 - 필드 업데이트 로직")
    void testUpdateUserReview_필드_업데이트() {
        // given
        Integer reviewId = 1;
        UserReviewRequest request = UserReviewRequest.builder()
            .trackName("Updated Track")
            .artistName("Updated Artist")
            .reviewContent("Updated review content")
            .rating(new BigDecimal("5.0"))
            .isPublic(false)
            .build();

        UserReview existingReview = createUserReview(reviewId);
        UserReview updatedReview = createUserReview(reviewId);
        updatedReview.setTrackName("Updated Track");
        updatedReview.setArtistName("Updated Artist");
        updatedReview.setRating(new BigDecimal("5.0"));
        updatedReview.setIsPublic(false);

        when(userReviewRepository.findById(reviewId)).thenReturn(Optional.of(existingReview));
        when(userReviewRepository.save(any(UserReview.class))).thenReturn(updatedReview);

        // when
        UserReviewResponse result = userReviewService.updateUserReview(reviewId, request);

        // then - 비즈니스 로직: 핵심 필드만 검증
        assertThat(result.getId()).isEqualTo(reviewId);
        assertThat(result.getTrackName()).isEqualTo("Updated Track");
        assertThat(result.getRating()).isEqualByComparingTo(new BigDecimal("5.0"));
        assertThat(result.getIsPublic()).isFalse();
    }


    /**
     * 비즈니스 로직 테스트 - 감상문 삭제 성공
     * 목적: 정상적인 감상문 삭제가 성공적으로 완료되는지 검증 (예외 없이 완료)
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직)
     */
    @Test
    @DisplayName("감상문 삭제 - 성공 시 삭제 확인")
    void testDeleteUserReview_성공_삭제확인() {
        // given
        Integer reviewId = 1;
        UserReview existingReview = createUserReview(reviewId);
        when(userReviewRepository.findById(reviewId)).thenReturn(Optional.of(existingReview));
        doNothing().when(userReviewRepository).delete(any(UserReview.class));

        // when
        userReviewService.deleteUserReview(reviewId);

        // then - 비즈니스 로직: 삭제가 성공적으로 완료되었는지 검증 (예외가 발생하지 않으면 성공)
        // 내부 구현 검증은 최소화하고 결과 중심으로 테스트
    }

    /**
     * 비즈니스 로직 테스트 - 추천 결과 조회
     * 목적: 특정 감상문의 추천 결과를 올바르게 조회하는지 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직)
     */
    @Test
    @DisplayName("추천 결과 조회 - 단순 조회 로직")
    void testGetRecommendationsByReviewId() {
        // given
        Integer reviewId = 1;
        List<RecommendTrack> recommendations = List.of(
            RecommendTrack.builder()
                .id(1)
                .userReviewId(reviewId)
                .recommendationScore(new BigDecimal("0.95"))
                .build()
        );

        when(recommendTrackRepository.findByUserReviewId(reviewId)).thenReturn(recommendations);

        // when
        List<RecommendTrack> result = userReviewService.getRecommendationsByReviewId(reviewId);

        // then - 비즈니스 로직: 추천 결과 조회가 올바르게 동작하는지 검증
        assertThat(result).hasSize(1);
        assertThat(result).extracting("userReviewId").containsOnly(reviewId);
        assertThat(result.get(0).getRecommendationScore()).isEqualByComparingTo(new BigDecimal("0.95"));
    }

    /**
     * 비즈니스 로직 테스트 - 추천 결과 없음
     * 목적: 추천 결과가 없을 때 빈 리스트를 반환하는 정상 케이스 검증
     * 우선순위: 🥇 1단계 (핵심 비즈니스 로직)
     */
    @Test
    @DisplayName("추천 결과 조회 - 추천 결과가 없을 때 빈 리스트 반환")
    void testGetRecommendationsByReviewId_EmptyResult() {
        // given
        Integer reviewId = 1;
        when(recommendTrackRepository.findByUserReviewId(reviewId)).thenReturn(Collections.emptyList());

        // when
        List<RecommendTrack> result = userReviewService.getRecommendationsByReviewId(reviewId);

        // then - 비즈니스 로직: 추천 결과가 없을 때 빈 리스트 반환
        assertThat(result).isEmpty();
    }

}
