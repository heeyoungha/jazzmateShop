package shop.jazzmate.jazzmateshop.criticsReview;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.web.bind.annotation.*;
import shop.jazzmate.jazzmateshop.criticsReview.dto.CriticsReviewResponse;
import shop.jazzmate.jazzmateshop.criticsReview.dto.CriticsReviewSummaryResponse;

import java.util.UUID;

@RestController
@RequestMapping("/api/critics")
@RequiredArgsConstructor
public class CriticsReviewController {

    private final CriticsReviewService criticsReviewService;

    @GetMapping
    public Page<CriticsReviewSummaryResponse> getReviews(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return criticsReviewService.getReviews(page, size)
                .map(CriticsReviewSummaryResponse::from);
    }

    @GetMapping("/{id}")
    public CriticsReviewResponse getReview(@PathVariable UUID id) {
        return CriticsReviewResponse.from(criticsReviewService.getReview(id));
    }
}
