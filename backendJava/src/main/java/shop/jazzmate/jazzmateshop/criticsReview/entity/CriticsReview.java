package shop.jazzmate.jazzmateshop.criticsReview.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "critics_reviews")
@Getter
@Builder
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@EqualsAndHashCode(onlyExplicitlyIncluded = true)
public class CriticsReview {

    @Id
    @EqualsAndHashCode.Include
    private UUID id;

    private String title;
    private String reviewer;
    private String reviewUrl;

    @Column(columnDefinition = "TEXT")
    private String reviewContent;

    @Column(columnDefinition = "TEXT")
    private String reviewSummary;

    @CreationTimestamp
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;
}
