package shop.jazzmate.jazzmateshop.criticsReview;

import jakarta.persistence.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "critics_review")
@Data
public class CriticsReview {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    private String title;
    private String reviewer;
    private String date;

    @Column(name = "url", length = 1000)  // 길이 늘리기
    private String url;

    @Column(columnDefinition = "text")
    private String content;

    @Column(columnDefinition = "text")
    private String albumInfo;

    @Column(columnDefinition = "text")
    private String youtubeInfo;

    private BigDecimal rating;

    @Column(columnDefinition = "text")
    private String trackListing;

    @Column(columnDefinition = "text")
    private String personnel;

    @Column(columnDefinition = "text")
    private String reviewSummary;

    private LocalDateTime createdAt;
}