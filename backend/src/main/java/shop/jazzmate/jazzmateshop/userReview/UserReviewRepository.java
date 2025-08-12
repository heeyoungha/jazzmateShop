package shop.jazzmate.jazzmateshop.userReview;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.util.List;

@Repository
public interface UserReviewRepository extends JpaRepository<UserReview, Integer> {
    
    /**
     * 사용자별 감상문 목록 조회 (최신순)
     */
    List<UserReview> findByUserIdOrderByCreatedAtDesc(String userId);
    
    /**
     * 공개된 감상문 목록 조회 (최신순)
     */
    List<UserReview> findByIsPublicTrueOrderByCreatedAtDesc();

}
