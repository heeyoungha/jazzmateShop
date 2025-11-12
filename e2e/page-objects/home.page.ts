/**
 * Home Page Object
 *
 * Represents the main landing page of JazzMate
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './base.page';

export class HomePage extends BasePage {
  // Locators
  readonly albumSearchInput: Locator;
  readonly searchButton: Locator;
  readonly navigationMenu: Locator;
  readonly writeReviewLink: Locator;
  readonly myReviewsLink: Locator;
  readonly recommendationsLink: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize locators
    this.albumSearchInput = page.getByPlaceholder(/앨범|검색|album|search/i);
    this.searchButton = page.getByRole('button', { name: /검색|search/i });
    this.navigationMenu = page.getByRole('navigation');
    this.writeReviewLink = page.getByRole('link', { name: /감상문 작성|리뷰 작성|write review/i });
    this.myReviewsLink = page.getByRole('link', { name: /내 감상문|my reviews/i });
    this.recommendationsLink = page.getByRole('link', { name: /추천|recommendations/i });
  }

  /**
   * Navigate to home page
   */
  async goto() {
    await super.goto('/');
  }

  /**
   * Search for an album
   */
  async searchAlbum(keyword: string) {
    await this.albumSearchInput.fill(keyword);
    await this.searchButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to write review page
   */
  async goToWriteReview() {
    await this.writeReviewLink.click();
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to my reviews page
   */
  async goToMyReviews() {
    await this.myReviewsLink.click();
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to recommendations page
   */
  async goToRecommendations() {
    await this.recommendationsLink.click();
    await this.page.waitForLoadState('networkidle');
  }
}
