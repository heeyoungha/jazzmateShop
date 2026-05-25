package shop.jazzmate.jazzmateshop.criticsReview;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;
import shop.jazzmate.jazzmateshop.criticsReview.entity.CriticsReview;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class CriticsReviewService {

    private final CriticsReviewRepository criticsReviewRepository;

    @Transactional(readOnly = true)
    public Page<CriticsReview> getReviews(int page, int size) {
        return criticsReviewRepository.findByReviewSummaryIsNotNull(PageRequest.of(page, size));
    }

    @Transactional(readOnly = true)
    public CriticsReview getReview(UUID id) {
        return criticsReviewRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("CriticsReview not found: " + id));
    }
}
