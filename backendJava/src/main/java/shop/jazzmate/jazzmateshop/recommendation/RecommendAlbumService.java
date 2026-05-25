package shop.jazzmate.jazzmateshop.recommendation;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.recommendation.dto.RecommendAlbumBatchRequest;
import shop.jazzmate.jazzmateshop.userReview.UserReviewRepository;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;
import shop.jazzmate.jazzmateshop.recommendation.entity.RecommendAlbum;

import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class RecommendAlbumService {

    private final RecommendAlbumRepository recommendAlbumRepository;
    private final UserReviewRepository userReviewRepository;

    // POST /api/user-reviews/{reviewId}/recommendations — FastAPI 콜백
    // albumId = v_album_embeddings.album_id (= embedding_vectors.id)
    @Transactional
    public void createRecommendAlbums(Integer reviewId, RecommendAlbumBatchRequest request) {
        UserReview review = userReviewRepository.findById(reviewId)
                .orElseThrow(() -> new ResourceNotFoundException("UserReview not found: " + reviewId));

        List<RecommendAlbum> albums = request.getRecommendations().stream()
                .map(item -> RecommendAlbum.builder()
                        .userReviewId(reviewId)
                        .albumId(item.getAlbumId())
                        .recommendationScore(item.getRecommendationScore())
                        .recommendationReason(item.getRecommendationReason())
                        .build())
                .toList();
        recommendAlbumRepository.saveAll(albums);
        
        review.completeRecommendation();

        log.info("추천 앨범 저장 완료: reviewId={}, savedCount={}", reviewId, albums.size());
    }
}
