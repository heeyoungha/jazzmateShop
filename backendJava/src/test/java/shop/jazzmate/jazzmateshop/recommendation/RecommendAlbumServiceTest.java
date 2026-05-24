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
import static org.mockito.Mockito.verify;

/**
 * RecommendAlbumService 단위 테스트
 *
 * 검증 범위:
 *  - createRecommendAlbums: saveAll() 일괄 저장 호출
 *  - createRecommendAlbums: 저장 완료 후 UserReview 상태 COMPLETED 전이
 */
@ExtendWith(MockitoExtension.class)
class RecommendAlbumServiceTest {

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
            given(userReviewRepository.findById(7)).willReturn(Optional.of(buildReview()));

            recommendAlbumService.createRecommendAlbums(7, buildBatchRequest(10));

            @SuppressWarnings("unchecked")
            ArgumentCaptor<List<RecommendAlbum>> captor = ArgumentCaptor.forClass(List.class);
            verify(recommendAlbumRepository).saveAll(captor.capture());

            List<RecommendAlbum> saved = captor.getValue();
            assertThat(saved).hasSize(1);
            assertThat(saved.get(0).getUserReviewId()).isEqualTo(7);
            assertThat(saved.get(0).getAlbumId()).isEqualTo(10);
        }

        @Test
        @DisplayName("3건 요청 → saveAll()에 3건 전달")
        void createRecommendAlbums_threeItems_savesBatch() {
            given(recommendAlbumRepository.saveAll(anyList())).willAnswer(i -> i.getArgument(0));
            given(userReviewRepository.findById(7)).willReturn(Optional.of(buildReview()));

            recommendAlbumService.createRecommendAlbums(7, buildBatchRequest(10, 11, 12));

            @SuppressWarnings("unchecked")
            ArgumentCaptor<List<RecommendAlbum>> captor = ArgumentCaptor.forClass(List.class);
            verify(recommendAlbumRepository).saveAll(captor.capture());

            assertThat(captor.getValue()).hasSize(3);
        }

        @Test
        @DisplayName("콜백 저장 완료 → UserReview 상태 COMPLETED 전이")
        void createRecommendAlbums_marksReviewCompleted() {
            UserReview review = buildReview();
            given(recommendAlbumRepository.saveAll(anyList())).willAnswer(i -> i.getArgument(0));
            given(userReviewRepository.findById(7)).willReturn(Optional.of(review));

            recommendAlbumService.createRecommendAlbums(7, buildBatchRequest(10));

            assertThat(review.getRecommendationStatus()).isEqualTo(RecommendationStatus.COMPLETED);
        }

        @Test
        @DisplayName("존재하지 않는 reviewId → ResourceNotFoundException")
        void createRecommendAlbums_reviewNotFound_throwsResourceNotFoundException() {
            given(recommendAlbumRepository.saveAll(anyList())).willAnswer(i -> i.getArgument(0));
            given(userReviewRepository.findById(999)).willReturn(Optional.empty());

            assertThatThrownBy(() -> recommendAlbumService.createRecommendAlbums(999, buildBatchRequest(10)))
                    .isInstanceOf(ResourceNotFoundException.class)
                    .hasMessageContaining("999");
        }
    }

    private RecommendAlbumBatchRequest buildBatchRequest(Integer... albumIds) {
        List<RecommendAlbumBatchRequest.Item> items = new ArrayList<>();
        for (Integer albumId : albumIds) {
            items.add(new RecommendAlbumBatchRequest.Item(
                    albumId,
                    new BigDecimal("0.9500"),
                    "분위기가 잘 맞습니다"
            ));
        }
        return new RecommendAlbumBatchRequest(items);
    }

    private UserReview buildReview() {
        return UserReview.builder()
                .id(7)
                .trackName("So What")
                .artistName("Miles Davis")
                .reviewContent("명반")
                .isPublic(true)
                .recommendationStatus(RecommendationStatus.PENDING)
                .build();
    }
}
