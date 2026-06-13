package shop.jazzmate.jazzmateshop.criticsReview.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "v_review_summary")
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

    @Column(name="url")
    private String reviewUrl;

    @Column(columnDefinition = "TEXT", name="content")
    private String reviewContent;

    @Column(columnDefinition = "TEXT")
    private String reviewSummary;

    private LocalDateTime createdAt;
}
