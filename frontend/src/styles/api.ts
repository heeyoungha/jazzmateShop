import { ApiResponse, Product, UserReview, CriticsReview } from '@/types';

const API_BASE_URL = '/api';

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${API_BASE_URL}${endpoint}`;
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    const response = await fetch(url, config);
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }

  // 제품 관련 API
  async getProducts(): Promise<ApiResponse<Product[]>> {
    return this.request<Product[]>('/products');
  }

  async getProduct(id: number): Promise<ApiResponse<Product>> {
    return this.request<Product>(`/products/${id}`);
  }

  // 사용자 리뷰 API
  async getUserReviews(productId: number): Promise<ApiResponse<UserReview[]>> {
    return this.request<UserReview[]>(`/products/${productId}/user-reviews`);
  }

  async createUserReview(review: Omit<UserReview, 'id' | 'createdAt' | 'updatedAt'>): Promise<ApiResponse<UserReview>> {
    return this.request<UserReview>('/user-reviews', {
      method: 'POST',
      body: JSON.stringify(review),
    });
  }

  // 비평가 리뷰 API
  async getCriticsReviews(productId: number): Promise<ApiResponse<CriticsReview[]>> {
    return this.request<CriticsReview[]>(`/products/${productId}/critics-reviews`);
  }
}

export const apiService = new ApiService();