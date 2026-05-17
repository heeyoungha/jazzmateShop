package shop.jazzmate.jazzmateshop.criticsReview;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.UUID;

@Repository
public interface CriticsReviewRepository extends JpaRepository<CriticsReview, UUID> {

    // reviewSummary가 null이 아닌 데이터만 페이지네이션으로 조회
    Page<CriticsReview> findByReviewSummaryIsNotNull(Pageable pageable);
}