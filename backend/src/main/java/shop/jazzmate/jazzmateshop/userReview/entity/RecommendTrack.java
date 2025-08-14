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

@Entity
@Table(name = "recommend_track")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecommendTrack {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;
    
    @Column(name = "user_review_id", nullable = false)
    private Integer userReviewId;
    
    @Column(name = "track_id", nullable = false)
    private Integer trackId;
    
    @Column(name = "recommendation_score", precision = 5, scale = 4, nullable = false)
    private BigDecimal recommendationScore;
    
    @Column(name = "recommendation_reason", columnDefinition = "TEXT", nullable = false)
    private String recommendationReason;
    
    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
    
    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
