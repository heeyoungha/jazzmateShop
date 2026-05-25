package shop.jazzmate.jazzmateshop.userReview;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

@Repository
public interface UserReviewRepository extends JpaRepository<UserReview, Integer> {

    Page<UserReview> findByIsPublicTrueOrderByCreatedAtDesc(Pageable pageable);

    // TODO: 인증 구현(JWT 등) 후 활성화
    Page<UserReview> findByUserIdOrderByCreatedAtDesc(String userId, Pageable pageable);
}
