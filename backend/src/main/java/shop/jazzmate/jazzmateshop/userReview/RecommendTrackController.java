package shop.jazzmate.jazzmateshop.userReview;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendTrack;

import java.time.LocalDateTime;

@RestController
@RequestMapping("/api/recommend-tracks")
@RequiredArgsConstructor
@Slf4j
public class RecommendTrackController {
    
    private final RecommendTrackRepository recommendTrackRepository;
    
    /**
     * RecommendTrack 생성 (Python API에서 호출)
     */
    @PostMapping
    public ResponseEntity<RecommendTrack> createRecommendTrack(@RequestBody RecommendTrack recommendTrack) {
        try {
            log.info("RecommendTrack 생성 요청: review_id={}, track_id={}", 
                recommendTrack.getUserReviewId(), recommendTrack.getTrackId());
            
            // 새 RecommendTrack 생성
            RecommendTrack newRecommendTrack = RecommendTrack.builder()
                .userReviewId(recommendTrack.getUserReviewId())
                .trackId(recommendTrack.getTrackId())
                .recommendationScore(recommendTrack.getRecommendationScore())
                .recommendationReason(recommendTrack.getRecommendationReason())
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
            
            RecommendTrack savedRecommendTrack = recommendTrackRepository.save(newRecommendTrack);
            log.info("RecommendTrack 생성 완료: {}", savedRecommendTrack.getId());
            
            return ResponseEntity.ok(savedRecommendTrack);
            
        } catch (Exception e) {
            log.error("RecommendTrack 생성 오류: ", e);
            return ResponseEntity.internalServerError().build();
        }
    }
}
