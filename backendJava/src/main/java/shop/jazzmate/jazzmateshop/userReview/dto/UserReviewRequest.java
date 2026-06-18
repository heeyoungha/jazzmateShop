package shop.jazzmate.jazzmateshop.userReview.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.util.UUID;

@Getter
@Builder
public class UserReviewRequest {

    @NotBlank
    private String albumName;

    @NotBlank
    private String artistName;

    @NotBlank
    private String reviewContent;
    
    // TODO: JWT 인증 구현 후 토큰에서 추출 예정
    private String userId;
    
    private UUID mbAlbumGid;
    private BigDecimal rating;
    private String mood;
    private String genre;
    private BigDecimal energyLevel;
    private Integer bpm;
    private String vocalStyle;
    private String instrumentation;
    private Boolean isPublic;
}
