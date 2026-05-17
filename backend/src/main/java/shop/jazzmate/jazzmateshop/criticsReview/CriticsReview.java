package shop.jazzmate.jazzmateshop.criticsReview;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "v_review_summary")
@Data
public class CriticsReview {

    @Id
    private UUID id;

    private String title;
    private String reviewer;

    @Column(name = "published_date")
    private String date;

    @Column(columnDefinition = "text")
    private String content;

    @Column(name = "review_summary", columnDefinition = "text")
    private String reviewSummary;

    private String url;

    private LocalDateTime createdAt;
}
