package shop.jazzmate.jazzmateshop.userReview;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewRequest;
import shop.jazzmate.jazzmateshop.userReview.dto.UserReviewResponse;
import shop.jazzmate.jazzmateshop.userReview.entity.UserReview;
import shop.jazzmate.jazzmateshop.userReview.entity.RecommendTrack;
import shop.jazzmate.jazzmateshop.userReview.entity.Track;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Slf4j
public class UserReviewService {
    
    private final UserReviewRepository userReviewRepository;
    private final RecommendTrackRepository recommendTrackRepository;
    private final TrackRepository trackRepository;
    
    /**
     * 감상문 작성
     */
    @Transactional
    public UserReviewResponse createUserReview(UserReviewRequest request) {
        try {
            log.info("감상문 생성 시작: album_id={}", request.getAlbumId());
            
            UserReview userReview = UserReview.builder()
                .albumId(request.getAlbumId())
                .userId(request.getUserId())
                .trackName(request.getTrackName())
                .artistName(request.getArtistName())
                .reviewContent(request.getReviewContent())
                .rating(request.getRating())
                .mood(request.getMood())
                .genre(request.getGenre())
                .energyLevel(request.getEnergyLevel())
                .bpm(request.getBpm())
                .vocalStyle(request.getVocalStyle())
                .instrumentation(request.getInstrumentation())
                .tags(request.getTags())
                .isPublic(request.getIsPublic())
                .isFeatured(false)
                .likeCount(0)
                .commentCount(0)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
            
            UserReview savedReview = userReviewRepository.save(userReview);
            
            log.info("감상문 생성 완료: id={}", savedReview.getId());
            
            
            return convertToResponse(savedReview);
            
        } catch (Exception e) {
            log.error("감상문 생성 오류: ", e);
            throw new RuntimeException("감상문 생성 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
    
    /**
     * 사용자 감상문 목록 조회
     */
    public List<UserReviewResponse> getUserReviews(String userId, int page, int size) {
        try {
            List<UserReview> reviews;
            
            if (userId != null && !userId.trim().isEmpty()) {
                reviews = userReviewRepository.findByUserIdOrderByCreatedAtDesc(userId);
            } else {
                reviews = userReviewRepository.findByIsPublicTrueOrderByCreatedAtDesc();
            }
            
            // 페이징 처리
            int start = page * size;
            int end = Math.min(start + size, reviews.size());
            
            if (start >= reviews.size()) {
                return List.of();
            }
            
            return reviews.subList(start, end).stream()
                .map(this::convertToResponse)
                .collect(Collectors.toList());
                
        } catch (Exception e) {
            log.error("감상문 목록 조회 오류: ", e);
            throw new RuntimeException("감상문 목록 조회 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
    
    /**
     * 특정 감상문 조회
     */
    public UserReviewResponse getUserReview(Integer id) {
        try {
            UserReview review = userReviewRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("감상문을 찾을 수 없습니다."));
            
            return convertToResponse(review);
            
        } catch (Exception e) {
            log.error("감상문 조회 오류: ", e);
            throw new RuntimeException("감상문 조회 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
    
    /**
     * 감상문 수정
     */
    public UserReviewResponse updateUserReview(Integer id, UserReviewRequest request) {
        try {
            UserReview existingReview = userReviewRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("감상문을 찾을 수 없습니다."));
            
            // 필드 업데이트
            existingReview.setTrackName(request.getTrackName());
            existingReview.setArtistName(request.getArtistName());
            existingReview.setReviewContent(request.getReviewContent());
            existingReview.setRating(request.getRating());
            existingReview.setMood(request.getMood());
            existingReview.setGenre(request.getGenre());
            existingReview.setEnergyLevel(request.getEnergyLevel());
            existingReview.setBpm(request.getBpm());
            existingReview.setVocalStyle(request.getVocalStyle());
            existingReview.setInstrumentation(request.getInstrumentation());
            existingReview.setTags(request.getTags());
            existingReview.setIsPublic(request.getIsPublic());
            existingReview.setUpdatedAt(LocalDateTime.now());
            
            UserReview updatedReview = userReviewRepository.save(existingReview);
            
            log.info("감상문 수정 완료: id={}", updatedReview.getId());
            
            return convertToResponse(updatedReview);
            
        } catch (Exception e) {
            log.error("감상문 수정 오류: ", e);
            throw new RuntimeException("감상문 수정 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
    
    /**
     * 감상문 삭제
     */
    public void deleteUserReview(Integer id) {
        try {
            UserReview review = userReviewRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("감상문을 찾을 수 없습니다."));
            
            userReviewRepository.delete(review);
            
            log.info("감상문 삭제 완료: id={}", id);
            
        } catch (Exception e) {
            log.error("감상문 삭제 오류: ", e);
            throw new RuntimeException("감상문 삭제 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
    
    /**
     * 특정 감상문의 추천 결과 조회
     */
    public List<RecommendTrack> getRecommendationsByReviewId(Integer reviewId) {
        return recommendTrackRepository.findByUserReviewIdOrderByScoreDesc(reviewId);
    }
    
    /**
     * 특정 감상문의 기존 추천 결과 삭제
     */
    @Transactional
    public void deleteRecommendationsByReviewId(Integer reviewId) {
        recommendTrackRepository.deleteByUserReviewId(reviewId);
        log.info("기존 추천 결과 삭제 완료: review_id={}", reviewId);
    }
    
    /**
     * UserReview 엔티티를 UserReviewResponse로 변환
     */
    private UserReviewResponse convertToResponse(UserReview review) {
        return UserReviewResponse.builder()
            .id(review.getId())
            .albumId(review.getAlbumId())
            .userId(review.getUserId())
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
            .build();
    }
}