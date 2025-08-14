package shop.jazzmate.jazzmateshop.userReview.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Entity
@Table(name = "user_reviews")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserReview {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "album_id")
    private Integer albumId;
    
    @Column(name = "user_id", length = 255)
    private String userId;
    
    @Column(name = "track_name", length = 255)
    private String trackName;

    @Column(name = "artist_name", length = 255) // 새로 추가
    private String artistName;

    @Column(name = "review_content", columnDefinition = "TEXT", nullable = false)
    private String reviewContent;
    
    @Column(name = "rating", precision = 3, scale = 1)
    private BigDecimal rating;
    
    @Column(name = "mood", length = 100)
    private String mood;
    
    @Column(name = "genre", length = 100)
    private String genre;

    @Column(name = "energy_level", precision = 3, scale = 2)
    private BigDecimal energyLevel;
    
    @Column(name = "bpm")
    private Integer bpm;

    @Column(name = "vocal_style", length = 100)
    private String vocalStyle;
    
    @Column(name = "instrumentation", length = 500)
    private String instrumentation;
    
    @ElementCollection
    @CollectionTable(name = "user_review_tags", joinColumns = @JoinColumn(name = "review_id"))
    @Column(name = "tag")
    private List<String> tags;

    @Column(name = "is_public")
    private Boolean isPublic;
    
    @Column(name = "is_featured")
    private Boolean isFeatured;
    
    @Column(name = "like_count")
    private Integer likeCount;
    
    @Column(name = "comment_count")
    private Integer commentCount;
    
    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
    
    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
