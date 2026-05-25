package shop.jazzmate.jazzmateshop.criticsReview;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import shop.jazzmate.jazzmateshop.criticsReview.entity.CriticsReview;

import java.util.UUID;

public interface CriticsReviewRepository extends JpaRepository<CriticsReview, UUID> {

    Page<CriticsReview> findByReviewSummaryIsNotNull(Pageable pageable);
}
