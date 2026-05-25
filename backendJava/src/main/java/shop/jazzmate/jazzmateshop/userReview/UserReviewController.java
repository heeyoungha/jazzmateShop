package shop.jazzmate.jazzmateshop.userReview;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import shop.jazzmate.jazzmateshop.common.constant.ApiMessages;
import shop.jazzmate.jazzmateshop.common.dto.ApiResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewCreateResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewSummaryResponse;

import java.util.List;

@RestController
@RequestMapping("/api/user-reviews")
@RequiredArgsConstructor
public class UserReviewController {

    private final UserReviewService userReviewService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<UserReviewCreateResponse> createUserReview(@Valid @RequestBody UserReviewRequest request) {
        UserReviewCreateResponse response = userReviewService.createUserReview(request);
        return ApiResponse.ok(ApiMessages.USER_REVIEW_CREATED, response);
    }

    @GetMapping("/{id}")
    public UserReviewResponse getUserReview(@PathVariable Integer id) {
        return userReviewService.getUserReview(id);
    }

    @GetMapping
    public List<UserReviewSummaryResponse> getPublicUserReviews(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return userReviewService.getPublicUserReviews(page, size);
    }

    @PostMapping("/{id}/retry")
    public ApiResponse<Void> retryRecommendation(@PathVariable Integer id) {
        userReviewService.retryRecommendation(id);
        return ApiResponse.ok(ApiMessages.RECOMMENDATION_RETRY_STARTED);
    }

}
