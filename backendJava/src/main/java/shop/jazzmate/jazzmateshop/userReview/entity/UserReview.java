package shop.jazzmate.jazzmateshop.userReview.entity;

import com.pgvector.PGvector;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.ColumnTransformer;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "user_reviews")
@Getter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class UserReview {

    @EqualsAndHashCode.Include
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "user_id", length = 255)
    private String userId;

    @Column(name = "mb_album_gid")
    private UUID mbAlbumGid;

    @Column(name = "album_name", length = 255)
    private String albumName;

    @Column(name = "artist_name", length = 255)
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

    @Column(name = "is_public")
    private Boolean isPublic;

    // FastAPI 추천 시 생성한 감상문 embedding. 추천 콜백으로 저장. NULL이면 미저장.
    @Convert(converter = PGvectorConverter.class)
    @ColumnTransformer(write = "?::vector")
    @Column(name = "review_embedding", columnDefinition = "vector(1536)")
    private PGvector reviewEmbedding;

    @Builder.Default
    @Enumerated(EnumType.STRING)
    @Column(name = "recommendation_status", length = 20)
    private RecommendationStatus recommendationStatus = RecommendationStatus.PENDING;

    @Builder.Default
    @Column(name = "is_featured")
    private Boolean isFeatured = false;

    @Builder.Default
    @Column(name = "like_count")
    private Integer likeCount = 0;

    @Builder.Default
    @Column(name = "comment_count")
    private Integer commentCount = 0;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    public void saveReviewEmbedding(List<Float> embedding) {
        float[] array = new float[embedding.size()];
        for (int i = 0; i < embedding.size(); i++) {
            array[i] = embedding.get(i);
        }
        this.reviewEmbedding = new PGvector(array);
    }

    public void retryRecommendation() {
        this.recommendationStatus = RecommendationStatus.PENDING;
    }

    public void completeRecommendation() {
        this.recommendationStatus = RecommendationStatus.COMPLETED;
    }

    public void failRecommendation() {
        this.recommendationStatus = RecommendationStatus.FAILED;
    }
}
