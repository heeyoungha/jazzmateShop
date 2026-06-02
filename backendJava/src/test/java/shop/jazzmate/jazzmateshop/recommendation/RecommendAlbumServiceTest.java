package shop.jazzmate.jazzmateshop.recommendation;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.recommendation.dto.RecommendAlbumBatchRequest;
import shop.jazzmate.jazzmateshop.recommendation.entity.RecommendAlbum;
import shop.jazzmate.jazzmateshop.userReview.UserReviewRepository;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendationStatus;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;


@ExtendWith(MockitoExtension.class)
class RecommendAlbumServiceTest {

    private static final int REVIEW_ID = 7;
    private static final int UNKNOWN_REVIEW_ID = 999;
    private static final String ALBUM_ID_10 = "00000000-0000-0000-0000-000000000010";
    private static final String ALBUM_ID_11 = "00000000-0000-0000-0000-000000000011";
    private static final String ALBUM_ID_12 = "00000000-0000-0000-0000-000000000012";
    private static final String FAILURE_ERROR_CODE = "NO_CANDIDATES";
    private static final String FAILURE_MESSAGE = "추천 후보가 없습니다.";

    @Mock
    RecommendAlbumRepository recommendAlbumRepository;

    @Mock
    UserReviewRepository userReviewRepository;

    @InjectMocks
    RecommendAlbumService recommendAlbumService;

    @Nested
    @DisplayName("createRecommendAlbums")
    class CreateRecommendAlbums {

        @Test
        @DisplayName("1건 요청 → saveAll()에 1건 전달")
        void createRecommendAlbums_oneItem_savesBatch() {
            given(recommendAlbumRepository.saveAll(anyList())).willAnswer(i -> i.getArgument(0));
            given(userReviewRepository.findById(REVIEW_ID)).willReturn(Optional.of(buildReview()));

            recommendAlbumService.createRecommendAlbums(REVIEW_ID, buildBatchRequest(ALBUM_ID_10));

            @SuppressWarnings("unchecked")
            ArgumentCaptor<List<RecommendAlbum>> captor = ArgumentCaptor.forClass(List.class);
            verify(recommendAlbumRepository).saveAll(captor.capture());

            List<RecommendAlbum> saved = captor.getValue();
            assertThat(saved).hasSize(1);
            assertThat(saved.get(0).getUserReviewId()).isEqualTo(REVIEW_ID);
            assertThat(saved.get(0).getAlbumId()).isEqualTo(ALBUM_ID_10);
        }

        @Test
        @DisplayName("3건 요청 → saveAll()에 3건 전달")
        void createRecommendAlbums_threeItems_savesBatch() {
            given(recommendAlbumRepository.saveAll(anyList())).willAnswer(i -> i.getArgument(0));
            given(userReviewRepository.findById(REVIEW_ID)).willReturn(Optional.of(buildReview()));

            recommendAlbumService.createRecommendAlbums(
                    REVIEW_ID,
                    buildBatchRequest(
                            ALBUM_ID_10,
                            ALBUM_ID_11,
                            ALBUM_ID_12
                    )
            );

            @SuppressWarnings("unchecked")
            ArgumentCaptor<List<RecommendAlbum>> captor = ArgumentCaptor.forClass(List.class);
            verify(recommendAlbumRepository).saveAll(captor.capture());

            assertThat(captor.getValue()).hasSize(3);
        }

        @Test
        @DisplayName("콜백 저장 완료 → UserReview 상태 COMPLETED 전이")
        void createRecommendAlbums_completedCallback_marksReviewCompleted() {
            UserReview review = buildReview();
            given(recommendAlbumRepository.saveAll(anyList())).willAnswer(i -> i.getArgument(0));
            given(userReviewRepository.findById(REVIEW_ID)).willReturn(Optional.of(review));

            recommendAlbumService.createRecommendAlbums(REVIEW_ID, buildBatchRequest(ALBUM_ID_10));

            assertThat(review.getRecommendationStatus()).isEqualTo(RecommendationStatus.COMPLETED);
        }

        @Test
        @DisplayName("FAILED 콜백 수신 → 저장 없이 UserReview 상태 FAILED 전이")
        void createRecommendAlbums_failedCallback_marksReviewFailed() {
            UserReview review = buildReview();
            given(userReviewRepository.findById(REVIEW_ID)).willReturn(Optional.of(review));

            recommendAlbumService.createRecommendAlbums(REVIEW_ID, buildFailedRequest());

            verify(recommendAlbumRepository, never()).saveAll(anyList());
            assertThat(review.getRecommendationStatus()).isEqualTo(RecommendationStatus.FAILED);
        }

        @Test
        @DisplayName("존재하지 않는 reviewId → ResourceNotFoundException")
        void createRecommendAlbums_reviewNotFound_throwsResourceNotFoundException() {
            given(userReviewRepository.findById(UNKNOWN_REVIEW_ID)).willReturn(Optional.empty());

            assertThatThrownBy(() -> recommendAlbumService.createRecommendAlbums(UNKNOWN_REVIEW_ID, buildBatchRequest(ALBUM_ID_10)))
                    .isInstanceOf(ResourceNotFoundException.class)
                    .hasMessageContaining(String.valueOf(UNKNOWN_REVIEW_ID));
        }
    }

    private RecommendAlbumBatchRequest buildBatchRequest(String... albumIds) {
        List<RecommendAlbumBatchRequest.Item> items = new ArrayList<>();
        for (String albumId : albumIds) {
            items.add(new RecommendAlbumBatchRequest.Item(
                    albumId,
                    new BigDecimal("0.9500"),
                    "분위기가 잘 맞습니다"
            ));
        }
        return new RecommendAlbumBatchRequest(
                RecommendationStatus.COMPLETED,
                items,
                null,
                null
        );
    }

    private RecommendAlbumBatchRequest buildFailedRequest() {
        return new RecommendAlbumBatchRequest(
                RecommendationStatus.FAILED,
                List.of(),
                FAILURE_ERROR_CODE,
                FAILURE_MESSAGE
        );
    }

    private UserReview buildReview() {
        return UserReview.builder()
                .id(REVIEW_ID)
                .trackName("So What")
                .artistName("Miles Davis")
                .reviewContent("명반")
                .isPublic(true)
                .recommendationStatus(RecommendationStatus.PENDING)
                .build();
    }
}
