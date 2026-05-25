package shop.jazzmate.jazzmateshop.userReview.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;

@Getter
@Builder
public class UserReviewRequest {

    @NotBlank
    private String trackName;

    @NotBlank
    private String artistName;

    @NotBlank
    private String reviewContent;

    private BigDecimal rating;
    private String mood;
    private String genre;
    private BigDecimal energyLevel;
    private Integer bpm;
    private String vocalStyle;
    private String instrumentation;
    private Boolean isPublic;
}
