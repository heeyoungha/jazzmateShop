package shop.jazzmate.jazzmateshop.userReview;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.recommendation.RecommendAlbumRepository;
import shop.jazzmate.jazzmateshop.recommendation.event.RecommendationRequestEvent;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewCreateResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewSummaryResponse;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendationStatus;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

/**
 * UserReviewService 단위 테스트
 *
 * 검증 범위:
 *  - createUserReview: 저장 후 RecommendationRequestEvent 발행 여부
 *  - createUserReview: 트랜잭션 내에서 AI 클라이언트 직접 호출 금지 (이벤트만 발행)
 *  - getPublicUserReviews: userId 유무에 따른 Repository 메서드 분기
 *  - getUserReview: 추천 유무에 따른 hasRecommendations 필드 세팅
 *  - getUserReview: 없는 id → ResourceNotFoundException
 *  - @Builder.Default 값(isFeatured=false, likeCount=0, commentCount=0) 확인
 */
@ExtendWith(MockitoExtension.class)
class UserReviewServiceTest {

    @Mock
    UserReviewRepository userReviewRepository;

    @Mock
    RecommendAlbumRepository recommendAlbumRepository;

    @Mock
    ApplicationEventPublisher eventPublisher;

    @InjectMocks
    UserReviewService userReviewService;

    // 공통 픽스처
    private final UserReview DEFAULT_SAVED = UserReview.builder()
            .id(1)
            .trackName("So What")
            .artistName("Miles Davis")
            .reviewContent("명반")
            .isPublic(true)
            .build();


    // ────────────────────────────────────────────────
    // createUserReview
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("createUserReview")
    class CreateUserReview {

        @BeforeEach
        void setUp() {
            given(userReviewRepository.save(any(UserReview.class))).willReturn(DEFAULT_SAVED);
        }

        @Test
        @DisplayName("저장 성공 → UserReviewCreateResponse 반환, id 포함")
        void create_success_returnsResponseWithId() {
            // given: @BeforeEach에서 save() stubbing 완료

            // when: 리뷰 생성 요청 실행
            UserReviewCreateResponse response = userReviewService.createUserReview(
                    buildRequest(DEFAULT_SAVED.getTrackName(), DEFAULT_SAVED.getArtistName(), DEFAULT_SAVED.getReviewContent()));

            // then: 반환된 Response에 저장된 엔티티의 id가 매핑되었는지 검증
            assertThat(response.getId()).isEqualTo(DEFAULT_SAVED.getId());
        }

        @Test
        @DisplayName("저장 후 RecommendationRequestEvent 발행 — reviewId, reviewContent 포함")
        void create_publishesRecommendationRequestEvent() {
            // given: @BeforeEach에서 save() stubbing 완료

            // when: 리뷰 생성 요청 실행
            userReviewService.createUserReview(
                    buildRequest(DEFAULT_SAVED.getTrackName(), DEFAULT_SAVED.getArtistName(), DEFAULT_SAVED.getReviewContent()));

            // then: 발행된 이벤트에 reviewId, reviewContent가 담겼는지 검증
            ArgumentCaptor<RecommendationRequestEvent> captor =
                    ArgumentCaptor.forClass(RecommendationRequestEvent.class);
            verify(eventPublisher).publishEvent(captor.capture()); //eventPublisher.publishEvent(...)가 호출되었는지 검증하고, 그때 전달된 이벤트 객체를 captor에 저장

            RecommendationRequestEvent event = captor.getValue();
            assertThat(event.reviewId()).isEqualTo(DEFAULT_SAVED.getId());
            assertThat(event.reviewContent()).isEqualTo(DEFAULT_SAVED.getReviewContent());
        }

        @Test
        @DisplayName("@Builder.Default — isFeatured=false, likeCount=0, commentCount=0")
        void create_builderDefaultValues() {
            // given: @BeforeEach에서 save() stubbing 완료
            ArgumentCaptor<UserReview> reviewCaptor = ArgumentCaptor.forClass(UserReview.class);

            // when: 리뷰 생성 요청 실행
            userReviewService.createUserReview(
                    buildRequest(DEFAULT_SAVED.getTrackName(), DEFAULT_SAVED.getArtistName(), DEFAULT_SAVED.getReviewContent()));

            // then: save()에 실제로 넘어간 객체를 꺼내어 @Builder.Default 기본값 검증
            verify(userReviewRepository).save(reviewCaptor.capture()); // save() 호출 확인 + 인자 캡처
            UserReview captured = reviewCaptor.getValue();             // 캡처된 객체 추출
            assertThat(captured.getIsFeatured()).isFalse();            // @Builder.Default: false
            assertThat(captured.getLikeCount()).isZero();              // @Builder.Default: 0
            assertThat(captured.getCommentCount()).isZero();           // @Builder.Default: 0
        }
    }

    // ────────────────────────────────────────────────
    // getPublicUserReviews — 공개 리뷰 목록 조회
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("getPublicUserReviews — 공개 리뷰 목록 조회")
    class GetUserReviews {

        @Test
        @DisplayName("결과 → UserReviewSummaryResponse(8개 필드)로 변환")
        void list_mapToSummaryResponse() {
            // given: 리뷰 1건이 담긴 Page 반환 stubbing
            given(userReviewRepository.findByIsPublicTrueOrderByCreatedAtDesc(any()))
                    .willReturn(new PageImpl<>(List.of(DEFAULT_SAVED)));

            // when: 목록 조회
            List<UserReviewSummaryResponse> result = userReviewService.getPublicUserReviews(0, 20);

            // then: UserReviewSummaryResponse로 변환되었는지 검증
            assertThat(result).hasSize(1);
            assertThat(result.get(0).getId()).isEqualTo(DEFAULT_SAVED.getId());
            assertThat(result.get(0).getTrackName()).isEqualTo(DEFAULT_SAVED.getTrackName());
        }
    }

    // ────────────────────────────────────────────────
    // getUserReview — 상세 조회
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("getUserReview — 상세 조회")
    class GetUserReview {

        @Test
        @DisplayName("COMPLETED — 추천 앨범 반환, hasRecommendations=true")
        void getById_completed_returnsRecommendations() {
            // given: COMPLETED 상태 리뷰 + 추천 앨범 1건
            UserReview completed = UserReview.builder()
                    .id(1).trackName("So What").artistName("Miles Davis")
                    .reviewContent("명반").isPublic(true)
                    .recommendationStatus(RecommendationStatus.COMPLETED)
                    .build();
            given(userReviewRepository.findById(1)).willReturn(Optional.of(completed));
            given(recommendAlbumRepository.findByUserReviewId(1))
                    .willReturn(List.of(mock(shop.jazzmate.jazzmateshop.recommendation.entity.RecommendAlbum.class)));

            // when: 리뷰 상세 조회
            UserReviewResponse result = userReviewService.getUserReview(1);

            // then: 추천 반환, 이벤트 재발행 안 함
            assertThat(result.isHasRecommendations()).isTrue();
            assertThat(result.getRecommendations()).isNotEmpty();
            verify(eventPublisher, never()).publishEvent(any());
        }

        @Test
        @DisplayName("PENDING — 처리 중 응답, 이벤트 재발행 안 함")
        void getById_pending_noEventPublished() {
            // given: PENDING 상태 리뷰 (DEFAULT_SAVED는 @Builder.Default로 PENDING)
            given(userReviewRepository.findById(DEFAULT_SAVED.getId())).willReturn(Optional.of(DEFAULT_SAVED));

            // when: 리뷰 상세 조회
            UserReviewResponse result = userReviewService.getUserReview(DEFAULT_SAVED.getId());

            // then: 빈 리스트 반환, 이벤트 재발행 안 함
            assertThat(result.getRecommendationStatus()).isEqualTo(RecommendationStatus.PENDING);
            assertThat(result.getRecommendations()).isEmpty();
            verify(eventPublisher, never()).publishEvent(any());
        }



        @Test
        @DisplayName("FAILED — 실패 응답, 이벤트 재발행 안 함")
        void getById_failed_noEventPublished() {
            UserReview failed = UserReview.builder()
                    .id(1).trackName("So What").artistName("Miles Davis")
                    .reviewContent("명반").isPublic(true)
                    .recommendationStatus(RecommendationStatus.FAILED)
                    .build();
            given(userReviewRepository.findById(1)).willReturn(Optional.of(failed));

            UserReviewResponse result = userReviewService.getUserReview(1);

            assertThat(result.getRecommendationStatus()).isEqualTo(RecommendationStatus.FAILED);
            assertThat(result.getRecommendations()).isEmpty();
            verify(eventPublisher, never()).publishEvent(any());
        }

        @Test
        @DisplayName("없는 id → ResourceNotFoundException")
        void getById_notFound_throwsResourceNotFoundException() {
            // given: 존재하지 않는 id로 조회 시 empty 반환
            given(userReviewRepository.findById(999)).willReturn(Optional.empty());

            // when & then: ResourceNotFoundException 발생, 메시지에 id 포함
            assertThatThrownBy(() -> userReviewService.getUserReview(999))
                    .isInstanceOf(ResourceNotFoundException.class)
                    .hasMessageContaining("999");
        }
    }

    // ────────────────────────────────────────────────
    // retryRecommendation
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("retryRecommendation — 재시도")
    class RetryRecommendation {

        @Test
        @DisplayName("FAILED 상태 → recommendationStatus=PENDING 전이 + RecommendationRequestEvent 재발행")
        void retry_failed_changesPendingAndPublishesEvent() {
            // given: FAILED 상태 리뷰
            UserReview failed = UserReview.builder()
                    .id(1).trackName("So What").artistName("Miles Davis")
                    .reviewContent("명반").isPublic(true)
                    .recommendationStatus(RecommendationStatus.FAILED)
                    .build();
            given(userReviewRepository.findById(1)).willReturn(Optional.of(failed));

            // when
            userReviewService.retryRecommendation(1);

            // then: PENDING 전이 + 이벤트 재발행
            assertThat(failed.getRecommendationStatus()).isEqualTo(RecommendationStatus.PENDING);
            verify(eventPublisher, times(1)).publishEvent(any(RecommendationRequestEvent.class));
        }

        @Test
        @DisplayName("존재하지 않는 id → ResourceNotFoundException")
        void retry_notFound_throwsResourceNotFoundException() {
            given(userReviewRepository.findById(999)).willReturn(Optional.empty());

            assertThatThrownBy(() -> userReviewService.retryRecommendation(999))
                    .isInstanceOf(ResourceNotFoundException.class)
                    .hasMessageContaining("999");
        }
    }

    // ────────────────────────────────────────────────
    // helpers
    // ────────────────────────────────────────────────
    private UserReviewRequest buildRequest(String track, String artist, String content) {
        return UserReviewRequest.builder()
                .trackName(track)
                .artistName(artist)
                .reviewContent(content)
                .build();
    }

}