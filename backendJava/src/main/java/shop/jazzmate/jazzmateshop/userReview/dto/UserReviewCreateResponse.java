package shop.jazzmate.jazzmateshop.userReview.dto;

import lombok.Getter;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;

@Getter
public class UserReviewCreateResponse {
    private final Integer id;

    private UserReviewCreateResponse(Integer id) {
        this.id = id;
    }

    public static UserReviewCreateResponse from(UserReview userReview) {
        return new UserReviewCreateResponse(userReview.getId());
    }
}
