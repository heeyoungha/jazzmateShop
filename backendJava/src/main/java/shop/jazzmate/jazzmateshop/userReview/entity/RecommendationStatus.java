package shop.jazzmate.jazzmateshop.userReview.entity;

public enum RecommendationStatus {
    PENDING,    // 생성 직후, AI 처리 중
    COMPLETED,  // 추천 앨범 저장 완료
    FAILED      // AI 처리 실패, 재시도 가능
}
