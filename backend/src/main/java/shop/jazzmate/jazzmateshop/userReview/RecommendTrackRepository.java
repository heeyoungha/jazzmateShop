package shop.jazzmate.jazzmateshop.userReview;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendTrack;

import java.util.List;

@Repository
public interface RecommendTrackRepository extends JpaRepository<RecommendTrack, Integer> {

    /**
     * 특정 감상문의 추천 결과 조회
     */
    List<RecommendTrack> findByUserReviewId(Integer userReviewId);

    /**
     * 특정 감상문의 추천 결과를 점수 순으로 조회
     */
    @Query("SELECT rt FROM RecommendTrack rt " +
            "WHERE rt.userReviewId = :reviewId " +
            "ORDER BY rt.recommendationScore DESC")
    List<RecommendTrack> findByUserReviewIdOrderByScoreDesc(@Param("reviewId") Integer reviewId);
}

