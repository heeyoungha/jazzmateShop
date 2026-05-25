package shop.jazzmate.jazzmateshop.userReview;

import lombok.RequiredArgsConstructor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.recommendation.RecommendAlbumRepository;
import shop.jazzmate.jazzmateshop.recommendation.entity.RecommendAlbum;
import shop.jazzmate.jazzmateshop.recommendation.event.RecommendationRequestEvent;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewCreateResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewSummaryResponse;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendationStatus;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

import java.util.List;

@Service
@RequiredArgsConstructor
public class UserReviewService {

    private final UserReviewRepository userReviewRepository;
    private final RecommendAlbumRepository recommendAlbumRepository;
    private final ApplicationEventPublisher eventPublisher;

    @Transactional
    public UserReviewCreateResponse createUserReview(UserReviewRequest request) {
        UserReview review = UserReview.builder()
                .trackName(request.getTrackName())
                .artistName(request.getArtistName())
                .reviewContent(request.getReviewContent())
                .rating(request.getRating())
                .mood(request.getMood())
                .genre(request.getGenre())
                .energyLevel(request.getEnergyLevel())
                .bpm(request.getBpm())
                .vocalStyle(request.getVocalStyle())
                .instrumentation(request.getInstrumentation())
                .isPublic(request.getIsPublic())
                .build();

        UserReview saved = userReviewRepository.save(review);
        eventPublisher.publishEvent(new RecommendationRequestEvent(saved.getId(), saved.getReviewContent()));

        return UserReviewCreateResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public List<UserReviewSummaryResponse> getPublicUserReviews(int page, int size) {
        return userReviewRepository
                .findByIsPublicTrueOrderByCreatedAtDesc(PageRequest.of(page, size))
                .map(UserReviewSummaryResponse::from)
                .toList();
    }

    @Transactional
    public void retryRecommendation(Integer id) {
        UserReview review = userReviewRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("UserReview not found: " + id));

        review.retryRecommendation();
        eventPublisher.publishEvent(new RecommendationRequestEvent(review.getId(), review.getReviewContent()));
    }

    @Transactional(readOnly = true)
    public UserReviewResponse getUserReview(Integer id) {
        UserReview review = userReviewRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("UserReview not found: " + id));

        List<RecommendAlbum> recommendations = review.getRecommendationStatus() == RecommendationStatus.COMPLETED
                ? recommendAlbumRepository.findByUserReviewId(id)
                : List.of();

        return UserReviewResponse.from(review, recommendations);
    }
}
