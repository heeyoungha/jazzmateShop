export const REVIEW_ID = 42;
export const CRITICS_ID = 100;

export const review = {
  id: REVIEW_ID,
  userId: "user-123",
  trackName: "So What",
  artistName: "Miles Davis",
  reviewContent: "처음 들었을 때의 그 고요함이 아직도 기억난다.",
  rating: 4.5,
  mood: "calm",
  genre: "modal jazz",
  energyLevel: 0.3,
  bpm: 120,
  vocalStyle: "instrumental",
  instrumentation: "quintet",
  isPublic: true,
  isFeatured: false,
  likeCount: 0,
  commentCount: 0,
  createdAt: "2026-05-23T10:00:00",
  updatedAt: "2026-05-23T10:01:00",
};

export const recommendation = {
  id: 1,
  userReviewId: REVIEW_ID,
  albumId: 101,
  recommendationReason: "모달 재즈 특유의 정적인 분위기가 유사합니다.",
  createdAt: "2026-05-23T10:01:00",
  updatedAt: "2026-05-23T10:01:00",
};

export const pendingReviewDetail = {
  review,
  recommendationStatus: "PENDING",
  hasRecommendations: false,
  recommendations: [],
};

export const completedReviewDetail = {
  review,
  recommendationStatus: "COMPLETED",
  hasRecommendations: true,
  recommendations: [recommendation],
};

export const failedReviewDetail = {
  review,
  recommendationStatus: "FAILED",
  hasRecommendations: false,
  recommendations: [],
};

export function userReviewPage({ number = 0, last = false } = {}) {
  return {
    content: [
      {
        id: REVIEW_ID + number,
        trackName: number === 0 ? "So What" : "Blue in Green",
        artistName: "Miles Davis",
        reviewContent: "처음 들었을 때의 그 고요함이 아직도 기억난다.",
        rating: 4.5,
        mood: "calm",
        genre: "modal jazz",
        createdAt: "2026-05-23T10:00:00",
      },
    ],
    totalElements: last ? 2 : 15,
    totalPages: last ? 2 : 3,
    number,
    size: 10,
    last,
  };
}

export function criticsPage({ number = 0, last = false } = {}) {
  return {
    content: [
      {
        id: CRITICS_ID + number,
        title: number === 0 ? "Kind of Blue Review" : "Blue Train Review",
        reviewer: "All About Jazz",
        date: "2026-05-23",
        reviewSummary: "정교한 앙상블과 절제된 긴장감이 돋보이는 리뷰입니다.",
      },
    ],
    totalElements: last ? 2 : 12,
    totalPages: last ? 2 : 3,
    number,
    size: 10,
    last,
  };
}

export const criticsDetail = {
  id: CRITICS_ID,
  title: "Kind of Blue Review",
  reviewer: "All About Jazz",
  date: "2026-05-23",
  reviewSummary: "정교한 앙상블과 절제된 긴장감이 돋보이는 리뷰입니다.",
  content: "전체 리뷰 본문입니다.",
  url: "https://www.allaboutjazz.com/example",
};
