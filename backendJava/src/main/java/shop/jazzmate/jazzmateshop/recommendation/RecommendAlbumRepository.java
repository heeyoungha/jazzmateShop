package shop.jazzmate.jazzmateshop.recommendation;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import shop.jazzmate.jazzmateshop.recommendation.entity.RecommendAlbum;

import java.util.List;

@Repository
public interface RecommendAlbumRepository extends JpaRepository<RecommendAlbum, Integer> {

    List<RecommendAlbum> findByUserReviewId(Integer userReviewId);
}
