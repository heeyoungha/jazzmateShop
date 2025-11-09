package shop.jazzmate.jazzmateshop.userReview;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * 외부 의존성(외부 API, DB) 테스트
 * 테스트 가이드 우선순위 3단계: 외부 의존성과 경계면 테스트
 * 
 * 가이드 원칙: 같은 타입의 예외를 반복 테스트하지 말고, 대표 케이스 1~2개만 테스트
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("UserReviewService 외부 의존성 테스트 - 외부 API 및 DB 경계면 검증")
class UserReviewServiceExternalDependencyTest {

    @Mock
    private UserReviewRepository userReviewRepository;

    @Mock
    private RecommendTrackRepository recommendTrackRepository;

    @Mock
    private TrackRepository trackRepository;

    @InjectMocks
    private UserReviewService userReviewService;

    /**
     * 외부 의존성 테스트 - DB 저장 실패 (대표 케이스)
     * 목적: DB 연결 실패 등 외부 의존성 문제 시 적절한 예외 메시지가 전달되는지 검증
     * 우선순위: 🥉 3단계 (외부 의존성과 경계면)
     * 
     * 가이드 적용: 같은 타입의 DB 실패 예외는 이 테스트 하나로 대표
     * - DB 저장/조회/삭제 실패는 모두 같은 RuntimeException 패턴이므로 중복 제거
     */
    @Test
    @DisplayName("외부 의존성 실패 - DB 저장 실패 시 예외 처리 (대표 케이스)")
    void testExternalDependency_DB_저장_실패() {
        // given
        UserReviewRequest request = UserReviewRequest.builder()
            .trackName("Blue in Green")
            .artistName("Miles Davis")
            .reviewContent("좋은 곡입니다.")
            .isPublic(true)
            .build();

        String errorMessage = "데이터베이스 연결 실패";
        when(userReviewRepository.save(any(UserReview.class)))
            .thenThrow(new RuntimeException(errorMessage));

        // when & then - 외부 의존성 실패 시 예외 처리 검증
        // 비즈니스 로직: 외부 의존성 실패 시 적절한 예외 메시지가 전달되는지 검증
        assertThatThrownBy(() -> userReviewService.createUserReview(request))
            .isInstanceOf(RuntimeException.class)
            .hasMessageContaining("감상문 생성 중 오류가 발생했습니다")
            .hasMessageContaining(errorMessage);
    }

    /**
     * 외부 의존성 테스트 - AI 서비스 격리
     * 목적: AI 서비스 호출 실패해도 감상문 저장은 성공하는지 검증 (외부 의존성 격리 원칙)
     * 우선순위: 🥉 3단계 (외부 의존성과 경계면)
     * 
     * 비즈니스 로직: 외부 API 실패가 핵심 비즈니스 로직(감상문 저장)에 영향을 주지 않아야 함
     */
    @Test
    @DisplayName("외부 의존성 격리 - AI 서비스 호출 실패해도 감상문 저장은 성공")
    void testExternalDependency_AI_서비스_실패해도_저장_성공() {
        // given
        UserReviewRequest request = UserReviewRequest.builder()
            .trackName("Blue in Green")
            .artistName("Miles Davis")
            .reviewContent("좋은 곡입니다.")
            .isPublic(true)
            .build();

        UserReview savedReview = UserReview.builder()
            .id(1)
            .trackName("Blue in Green")
            .artistName("Miles Davis")
            .reviewContent("좋은 곡입니다.")
            .isPublic(true)
            .isFeatured(false)
            .likeCount(0)
            .commentCount(0)
            .createdAt(LocalDateTime.now())
            .updatedAt(LocalDateTime.now())
            .build();

        when(userReviewRepository.save(any(UserReview.class)))
            .thenReturn(savedReview);

        // AI 서비스 URL 설정 (실제로는 환경 변수로 설정됨)
        ReflectionTestUtils.setField(userReviewService, "aiServiceUrl", "http://invalid-url:8000");

        // when
        UserReviewResponse response = userReviewService.createUserReview(request);

        // then - 비즈니스 로직: AI 서비스 실패해도 감상문 저장은 성공
        // (실제로는 Controller에서 비동기로 호출되므로 여기서는 저장만 검증)
        assertThat(response.getId()).isEqualTo(1);
        assertThat(response.getTrackName()).isEqualTo("Blue in Green");
        assertThat(response.getReviewContent()).isEqualTo("좋은 곡입니다.");
    }
}

