package shop.jazzmate.jazzmateshop.criticsReview;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.criticsReview.entity.CriticsReview;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
class CriticsReviewServiceTest {

    @Mock
    CriticsReviewRepository criticsReviewRepository;

    @InjectMocks
    CriticsReviewService criticsReviewService;

    // 공통 픽스처
    private static final UUID DEFAULT_ID = UUID.fromString("00000000-0000-0000-0000-000000000001");
    private final CriticsReview DEFAULT_REVIEW = CriticsReview.builder()
            .id(DEFAULT_ID)
            .title("Kind of Blue")
            .reviewer("홍길동")
            .reviewSummary("재즈 명반 리뷰")
            .build();

    // ────────────────────────────────────────────────
    // getReviews
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("getReviews — 페이지네이션")
    class GetReviews {

        @Test
        @DisplayName("15건 중 page=0&size=10 → content.size()==10, last==false")
        void getReviews_firstPage_returnsPageWithLastFalse() {
            List<CriticsReview> content = java.util.Collections.nCopies(10, DEFAULT_REVIEW);
            given(criticsReviewRepository.findByReviewSummaryIsNotNull(any()))
                    .willReturn(new PageImpl<>(content, PageRequest.of(0, 10), 15));

            Page<CriticsReview> result = criticsReviewService.getReviews(0, 10);

            assertThat(result.getContent()).hasSize(10);
            assertThat(result.isLast()).isFalse();
        }

        @Test
        @DisplayName("15건 중 page=1&size=10 → content.size()==5, last==true")
        void getReviews_lastPage_returnsPageWithLastTrue() {
            List<CriticsReview> content = java.util.Collections.nCopies(5, DEFAULT_REVIEW);
            given(criticsReviewRepository.findByReviewSummaryIsNotNull(any()))
                    .willReturn(new PageImpl<>(content, PageRequest.of(1, 10), 15));

            Page<CriticsReview> result = criticsReviewService.getReviews(1, 10);

            assertThat(result.getContent()).hasSize(5);
            assertThat(result.isLast()).isTrue();
        }
    }

    // ────────────────────────────────────────────────
    // getReview
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("getReview — 단건 조회")
    class GetReview {

        @Test
        @DisplayName("존재하는 id → CriticsReview 반환")
        void getReview_existingId_returnsCriticsReview() {
            given(criticsReviewRepository.findById(DEFAULT_ID)).willReturn(Optional.of(DEFAULT_REVIEW));

            CriticsReview result = criticsReviewService.getReview(DEFAULT_ID);

            assertThat(result.getId()).isEqualTo(DEFAULT_ID);
        }

        @Test
        @DisplayName("존재하지 않는 id → ResourceNotFoundException")
        void getReview_notFound_throwsResourceNotFoundException() {
            UUID unknownId = UUID.fromString("00000000-0000-0000-0000-000000000999");
            given(criticsReviewRepository.findById(unknownId)).willReturn(Optional.empty());

            assertThatThrownBy(() -> criticsReviewService.getReview(unknownId))
                    .isInstanceOf(ResourceNotFoundException.class);
        }
    }

}
