package shop.jazzmate.jazzmateshop.userReview;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewWithRecommendationsResponse;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendTrack;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/user-reviews")
@RequiredArgsConstructor
@Slf4j
public class UserReviewController {
    
    private final UserReviewService userReviewService;
    
    /**
     * 감상문 작성
     */
    @PostMapping
    public ResponseEntity<Map<String, Object>> createUserReview(
            @RequestBody UserReviewRequest request) {
        try {
            log.info("감상문 작성 요청: album_id={}, track_name={}", request.getAlbumId(), request.getTrackName());
            log.info("요청 데이터: reviewContent={}, artistName={}", request.getReviewContent(), request.getArtistName());
            
            UserReviewResponse response = userReviewService.createUserReview(request);
            
            // 감상문 저장 완료 후 Python API 호출하여 추천 생성 (비동기)
            try {
                log.info("추천 생성 시작: review_id={}", response.getId());
                userReviewService.generateRecommendationsForReview(response.getId(), response.getReviewContent());
                log.info("추천 생성 요청 완료: review_id={} (비동기 처리 중)", response.getId());
            } catch (Exception e) {
                log.error("추천 생성 실패: review_id={}, error={}", response.getId(), e.getMessage());
            }
            
            Map<String, Object> result = Map.of(
                "success", true,
                "message", "감상문이 성공적으로 저장되었습니다.",
                "data", response
            );
            
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("감상문 작성 오류: ", e);
            Map<String, Object> errorResponse = Map.of(
                "success", false,
                "message", e.getMessage()
            );
            return ResponseEntity.internalServerError().body(errorResponse);
        }
    }
    
    /**
     * 사용자 감상문 목록 조회
     */
    @GetMapping
    public ResponseEntity<List<UserReviewResponse>> getUserReviews(
            @RequestParam(required = false) String userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        try {
            List<UserReviewResponse> reviews = userReviewService.getUserReviews(userId, page, size);
            return ResponseEntity.ok(reviews);
        } catch (Exception e) {
            log.error("감상문 목록 조회 오류: ", e);
            return ResponseEntity.internalServerError().build();
        }
    }
    
    /**
     * 특정 감상문 조회
     */
    @GetMapping("/{id}")
    public ResponseEntity<UserReviewWithRecommendationsResponse> getUserReview(@PathVariable Integer id) {
        try {
            UserReviewResponse review = userReviewService.getUserReview(id);
            
            // 추천 결과 조회
            List<RecommendTrack> recommendations = userReviewService.getRecommendationsByReviewId(id);
          
            // 통합 응답 생성
            UserReviewWithRecommendationsResponse response = UserReviewWithRecommendationsResponse.builder()
                .id(review.getId())
                .albumId(review.getAlbumId())
                .trackName(review.getTrackName())
                .artistName(review.getArtistName())
                .reviewContent(review.getReviewContent())
                .rating(review.getRating())
                .mood(review.getMood())
                .genre(review.getGenre())
                .energyLevel(review.getEnergyLevel())
                .bpm(review.getBpm())
                .vocalStyle(review.getVocalStyle())
                .instrumentation(review.getInstrumentation())
                .tags(review.getTags())
                .isPublic(review.getIsPublic())
                .isFeatured(review.getIsFeatured())
                .likeCount(review.getLikeCount())
                .commentCount(review.getCommentCount())
                .createdAt(review.getCreatedAt())
                .updatedAt(review.getUpdatedAt())
                .recommendations(recommendations)
                .hasRecommendations(!recommendations.isEmpty())
                .build();
            
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("감상문 조회 오류: ", e);
            return ResponseEntity.notFound().build();
        }
    }
    
    /**
     * 감상문 수정
     */
    @PutMapping("/{id}")
    public ResponseEntity<Map<String, Object>> updateUserReview(
            @PathVariable Integer id,
            @RequestBody UserReviewRequest request) {
        try {
            UserReviewResponse response = userReviewService.updateUserReview(id, request);
            
            Map<String, Object> result = Map.of(
                "success", true,
                "message", "감상문이 성공적으로 수정되었습니다.",
                "data", response
            );
            
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("감상문 수정 오류: ", e);
            Map<String, Object> errorResponse = Map.of(
                "success", false,
                "message", e.getMessage()
            );
            return ResponseEntity.internalServerError().body(errorResponse);
        }
    }
    
    /**
     * 감상문 삭제
     */
    @DeleteMapping("/{id}")
    public ResponseEntity<Map<String, Object>> deleteUserReview(@PathVariable Integer id) {
        try {
            userReviewService.deleteUserReview(id);
            
            Map<String, Object> result = Map.of(
                "success", true,
                "message", "감상문이 성공적으로 삭제되었습니다."
            );
            
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("감상문 삭제 오류: ", e);
            Map<String, Object> errorResponse = Map.of(
                "success", false,
                "message", e.getMessage()
            );
            return ResponseEntity.internalServerError().body(errorResponse);
        }
    }
    
    /**
     * 특정 감상문의 추천 결과 조회
     */
    @GetMapping("/{id}/recommendations")
    public ResponseEntity<List<RecommendTrack>> getRecommendations(@PathVariable Integer id) {
        try {
            List<RecommendTrack> recommendations = userReviewService.getRecommendationsByReviewId(id);
            return ResponseEntity.ok(recommendations);
        } catch (Exception e) {
            log.error("추천 조회 오류: ", e);
            return ResponseEntity.internalServerError().build();
        }
    }
}
