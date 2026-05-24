package shop.jazzmate.jazzmateshop.userReview;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * UserReviewRepository @DataJpaTest
 *
 * 검증 범위:
 *  - findByIsPublicTrueOrderByCreatedAtDesc: 공개 리뷰만 최신순 조회
 *  - findByUserIdOrderByCreatedAtDesc: userId 기반 조회
 *  - 페이징(Pageable) 동작 확인
 *  - @CreationTimestamp / @UpdateTimestamp 자동 세팅
 *  - @Builder.Default 값 검증
 */
@DataJpaTest
class UserReviewRepositoryTest {

    @Autowired
    UserReviewRepository userReviewRepository;

    @BeforeEach
    void setUp() {
        userReviewRepository.deleteAll();
    }

    // ────────────────────────────────────────────────
    // findByIsPublicTrueOrderByCreatedAtDesc
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("공개 리뷰 최신순 조회")
    class FindPublicReviews {

        @Test
        @DisplayName("isPublic=true 만 반환, isPublic=false 제외")
        void returnsOnlyPublicReviews() {
            save("So What", "Miles Davis", "명반", true, "user1");
            save("Blue", "Bill Evans", "서정적", false, "user2");

            Pageable pageable = PageRequest.of(0, 10);
            Page<UserReview> result = userReviewRepository
                    .findByIsPublicTrueOrderByCreatedAtDesc(pageable);

            assertThat(result.getContent()).hasSize(1);
            assertThat(result.getContent().get(0).getTrackName()).isEqualTo("So What");
        }

        @Test
        @DisplayName("최신순(createdAt DESC) 정렬 확인")
        void orderedByCreatedAtDesc() throws InterruptedException {
            save("First", "A", "content1", true, "user1");
            Thread.sleep(10);   // 타임스탬프 차이 보장
            save("Second", "B", "content2", true, "user2");

            Page<UserReview> result = userReviewRepository
                    .findByIsPublicTrueOrderByCreatedAtDesc(PageRequest.of(0, 10));

            assertThat(result.getContent().get(0).getTrackName()).isEqualTo("Second");
            assertThat(result.getContent().get(1).getTrackName()).isEqualTo("First");
        }

        @Test
        @DisplayName("Pageable — size=1 이면 1건만 반환")
        void pagingWorks() {
            save("T1", "A1", "c1", true, "u1");
            save("T2", "A2", "c2", true, "u2");
            save("T3", "A3", "c3", true, "u3");

            Page<UserReview> firstPage = userReviewRepository
                    .findByIsPublicTrueOrderByCreatedAtDesc(PageRequest.of(0, 1));

            assertThat(firstPage.getContent()).hasSize(1);
            assertThat(firstPage.getTotalElements()).isEqualTo(3);
            assertThat(firstPage.isLast()).isFalse();
        }
    }

    // ────────────────────────────────────────────────
    // findByUserIdOrderByCreatedAtDesc
    // ────────────────────────────────────────────────
    // TODO: 인증 구현(JWT 등) 후 userId가 실제로 저장될 때 findByUserIdOrderByCreatedAtDesc 테스트 추가

    // ────────────────────────────────────────────────
    // @Builder.Default / 타임스탬프 자동 세팅
    // ────────────────────────────────────────────────
    @Nested
    @DisplayName("엔티티 저장 — @Builder.Default, 타임스탬프")
    class EntityDefaults {

        @Test
        @DisplayName("isFeatured=false, likeCount=0, commentCount=0 기본값")
        void builderDefaults() {
            UserReview saved = save("T", "A", "c", true, "u");

            assertThat(saved.getIsFeatured()).isFalse();
            assertThat(saved.getLikeCount()).isZero();
            assertThat(saved.getCommentCount()).isZero();
        }

        @Test
        @DisplayName("@CreationTimestamp / @UpdateTimestamp 자동 세팅")
        void timestampsAutoSet() {
            UserReview saved = save("T", "A", "c", true, "u");

            assertThat(saved.getCreatedAt()).isNotNull();
            assertThat(saved.getUpdatedAt()).isNotNull();
        }
    }

    // ────────────────────────────────────────────────
    // helper
    // ────────────────────────────────────────────────
    private UserReview save(String track, String artist, String content,
                            boolean isPublic, String userId) {
        UserReview review = UserReview.builder()
                .trackName(track)
                .artistName(artist)
                .reviewContent(content)
                .isPublic(isPublic)
                .userId(userId)
                .build();
        return userReviewRepository.save(review);
    }
}