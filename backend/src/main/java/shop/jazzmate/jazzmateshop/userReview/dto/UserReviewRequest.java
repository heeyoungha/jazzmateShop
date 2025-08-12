package shop.jazzmate.jazzmateshop.userReview.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserReviewRequest {
    @JsonProperty("album_id")
    private Integer albumId;

    @JsonProperty("user_id")
    private String userId;

    @JsonProperty("track_name")
    private String trackName;

    @JsonProperty("artist_name")
    private String artistName;

    @JsonProperty("review_content")
    private String reviewContent;

    private BigDecimal rating;
    private String mood;
    private String genre;

    @JsonProperty("energy_level")
    private BigDecimal energyLevel;

    private Integer bpm;

    @JsonProperty("vocal_style")
    private String vocalStyle;

    private String instrumentation;
    private List<String> tags;

    @JsonProperty("is_public")
    private Boolean isPublic;
}