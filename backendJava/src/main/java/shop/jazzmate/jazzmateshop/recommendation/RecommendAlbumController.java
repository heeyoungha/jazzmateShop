package shop.jazzmate.jazzmateshop.recommendation;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import shop.jazzmate.jazzmateshop.recommendation.dto.RecommendAlbumCallbackRequest;

@RestController
@RequestMapping("/api/user-reviews")
@RequiredArgsConstructor
public class RecommendAlbumController {

    private final RecommendAlbumService recommendAlbumService;

    @PostMapping("/{reviewId}/recommendations")
    public void createRecommendations(
            @PathVariable Integer reviewId,
            @Valid @RequestBody RecommendAlbumCallbackRequest request) {
        recommendAlbumService.createRecommendAlbums(reviewId, request);
    }
}
