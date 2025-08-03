// API 응답 타입
export interface ApiResponse<T> {
    data: T;
    message: string;
    status: number;
  }
  
  // 사용자 리뷰 타입
  export interface UserReview {
    id: number;
    userId: number;
    productId: number;
    rating: number;
    comment: string;
    createdAt: string;
    updatedAt: string;
  }
  
  // 비평가 리뷰 타입
  export interface CriticsReview {
    id: number;
    criticId: number;
    productId: number;
    title: string;
    content: string;
    rating: number;
    publishedAt: string;
  }
  
  // 제품 타입
  export interface Product {
    id: number;
    name: string;
    description: string;
    price: number;
    category: string;
    imageUrl: string;
    userReviews: UserReview[];
    criticsReviews: CriticsReview[];
  }