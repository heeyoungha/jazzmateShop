package shop.jazzmate.jazzmateshop.album.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "album")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Album {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;
    
    @Column(name = "album_artist", length = 255)
    private String albumArtist;
    
    @Column(name = "album_title", length = 255)
    private String albumTitle;
    
    @Column(name = "album_year")
    private Integer albumYear;
    
    @Column(name = "album_label", length = 255)
    private String albumLabel;
    
    @Column(name = "track_listing", columnDefinition = "jsonb")
    private String trackListing;
    
    @Column(name = "critics_review_id")
    private Integer criticsReviewId;
    
    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
    
    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
