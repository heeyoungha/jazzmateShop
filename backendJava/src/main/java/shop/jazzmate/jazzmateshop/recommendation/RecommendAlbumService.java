package shop.jazzmate.jazzmateshop.recommendation;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.recommendation.dto.RecommendAlbumCallbackRequest;
import shop.jazzmate.jazzmateshop.userReview.UserReviewRepository;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendationStatus;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;
import shop.jazzmate.jazzmateshop.recommendation.entity.RecommendAlbum;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class RecommendAlbumService {

    private final RecommendAlbumRepository recommendAlbumRepository;
    private final UserReviewRepository userReviewRepository;

    // POST /api/user-reviews/{reviewId}/recommendations — FastAPI 콜백
    // albumId = v_embedding_with_album.album_id (= embedding_vectors.id)
    @Transactional
    public void createRecommendAlbums(Integer reviewId, RecommendAlbumCallbackRequest request) {
        UserReview review = userReviewRepository.findById(reviewId)
                .orElseThrow(() -> new ResourceNotFoundException("UserReview not found: " + reviewId));

        RecommendationStatus status = request.getStatus();
        if (status == null) {
            throw new IllegalArgumentException("recommendation status is required");
        }

        if (status == RecommendationStatus.FAILED) {
            review.failRecommendation();
            log.info("추천 처리 실패 콜백 수신: reviewId={}, errorCode={}, message={}",
                    reviewId, request.getErrorCode(), request.getMessage());
            return;
        }

        if (status != RecommendationStatus.COMPLETED) {
            throw new IllegalArgumentException("unsupported recommendation status: " + status);
        }

        List<RecommendAlbum> albums = request.getRecommendations().stream()
                .map(item -> RecommendAlbum.builder()
                        .userReviewId(reviewId)
                        .albumId(UUID.fromString(item.getAlbumId()))
                        .criticsReviewId(item.getCriticsReviewId())
                        .albumArtist(item.getAlbumArtist())
                        .albumTitle(item.getAlbumTitle())
                        .recommendationScore(item.getRecommendationScore())
                        .recommendationReason(item.getRecommendationReason())
                        .build())
                .toList();
        recommendAlbumRepository.saveAll(albums);
        
        review.completeRecommendation();

        log.info("추천 앨범 저장 완료: reviewId={}, savedCount={}", reviewId, albums.size());
    }
}
