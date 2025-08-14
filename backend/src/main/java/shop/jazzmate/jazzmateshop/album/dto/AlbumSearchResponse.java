package shop.jazzmate.jazzmateshop.album.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AlbumSearchResponse {
    private Integer id;
    private String albumArtist;
    private String albumTitle;
    private Integer albumYear;
    private String albumLabel;
    private String trackListing;
    private Integer criticsReviewId;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
