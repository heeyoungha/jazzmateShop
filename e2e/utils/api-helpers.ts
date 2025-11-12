/**
 * API Helper Functions for E2E Tests
 *
 * Provides utility functions for making API calls and validating responses
 */

import { APIRequestContext, expect } from '@playwright/test';

export class ApiHelpers {
  constructor(private request: APIRequestContext) {}

  /**
   * Create a new user review via API
   */
  async createUserReview(reviewData: {
    userId: string;
    trackName: string;
    albumName: string;
    artistName: string;
    reviewContent: string;
    rating: number;
    isPublic: boolean;
  }) {
    const response = await this.request.post('/api/user-reviews', {
      data: reviewData,
    });
    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  /**
   * Search for albums by keyword
   */
  async searchAlbums(keyword: string) {
    const response = await this.request.get(`/api/albums/search?keyword=${encodeURIComponent(keyword)}`);
    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  /**
   * Get user reviews by user ID
   */
  async getUserReviews(userId: string) {
    const response = await this.request.get(`/api/user-reviews?userId=${userId}`);
    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  /**
   * Get recommendations for a review
   */
  async getRecommendations(reviewId: number) {
    const response = await this.request.get(`/api/user-reviews/${reviewId}/recommendations`);
    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  /**
   * Delete a user review (cleanup)
   */
  async deleteUserReview(reviewId: number) {
    const response = await this.request.delete(`/api/user-reviews/${reviewId}`);
    expect(response.ok()).toBeTruthy();
  }

  /**
   * Wait for async recommendation generation to complete
   * Polls the recommendations endpoint until data is available
   */
  async waitForRecommendations(reviewId: number, maxAttempts = 10, delayMs = 1000): Promise<any> {
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const response = await this.request.get(`/api/user-reviews/${reviewId}/recommendations`);
        if (response.ok()) {
          const data = await response.json();
          if (data && data.length > 0) {
            return data;
          }
        }
      } catch (error) {
        // Continue polling
      }
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
    throw new Error(`Recommendations not generated after ${maxAttempts} attempts`);
  }
}

/**
 * Validate API response structure
 */
export function validateUserReviewResponse(response: any) {
  expect(response).toHaveProperty('id');
  expect(response).toHaveProperty('userId');
  expect(response).toHaveProperty('trackName');
  expect(response).toHaveProperty('albumName');
  expect(response).toHaveProperty('artistName');
  expect(response).toHaveProperty('reviewContent');
  expect(response).toHaveProperty('rating');
  expect(response).toHaveProperty('isPublic');
  expect(response).toHaveProperty('createdAt');
}

export function validateRecommendationResponse(response: any) {
  expect(response).toHaveProperty('id');
  expect(response).toHaveProperty('trackName');
  expect(response).toHaveProperty('albumName');
  expect(response).toHaveProperty('artistName');
  expect(response).toHaveProperty('similarityScore');
  expect(response).toHaveProperty('recommendationReason');
}

export function validateAlbumSearchResponse(response: any) {
  expect(Array.isArray(response)).toBeTruthy();
  if (response.length > 0) {
    expect(response[0]).toHaveProperty('albumName');
    expect(response[0]).toHaveProperty('artistName');
  }
}
