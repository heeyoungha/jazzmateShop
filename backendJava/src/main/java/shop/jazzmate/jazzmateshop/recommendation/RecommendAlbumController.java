package shop.jazzmate.jazzmateshop.recommendation;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import io.swagger.v3.oas.annotations.tags.Tag;
import shop.jazzmate.jazzmateshop.recommendation.dto.RecommendAlbumCallbackRequest;

@Tag(name = "recommendations", description = "AI 추천 결과 콜백 수신")
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
