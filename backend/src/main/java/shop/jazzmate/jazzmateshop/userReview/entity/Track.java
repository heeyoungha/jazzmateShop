package shop.jazzmate.jazzmateshop.userReview.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "track")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Track {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;
    
    @Column(name = "album_id")
    private Integer albumId;
    
    @Column(name = "track_title", nullable = false)
    private String trackTitle;
    
    @Column(name = "artist_name", nullable = false)
    private String artistName;
    
    @Column(name = "genre")
    private String genre;
    
    @Column(name = "mood")
    private String mood;
    
    @Column(name = "energy")
    private Double energy;
    
    @Column(name = "bpm")
    private Integer bpm;
    
    @Column(name = "vocal_style")
    private String vocalStyle;
    
    @Column(name = "instrumentation")
    private String instrumentation;
    
    @Column(name = "lyrics", columnDefinition = "TEXT")
    private String lyrics;
    
    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
    
    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
