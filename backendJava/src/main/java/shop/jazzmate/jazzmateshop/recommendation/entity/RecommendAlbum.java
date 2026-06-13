package shop.jazzmate.jazzmateshop.recommendation.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "recommend_album")
@Getter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class RecommendAlbum {

    @EqualsAndHashCode.Include
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "user_review_id", nullable = false)
    private Integer userReviewId;

    @Column(name = "album_id", nullable = false)
    private UUID albumId;

    @Column(name = "critics_review_id", nullable = false)
    private UUID criticsReviewId;

    @Column(name = "album_artist")
    private String albumArtist;

    @Column(name = "album_title")
    private String albumTitle;

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
