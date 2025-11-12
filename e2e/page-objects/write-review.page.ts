/**
 * Write Review Page Object
 *
 * Represents the review submission page
 */

import { Page, Locator } from '@playwright/test';
import { BasePage } from './base.page';

export class WriteReviewPage extends BasePage {
  // Locators
  readonly trackNameInput: Locator;
  readonly albumNameInput: Locator;
  readonly artistNameInput: Locator;
  readonly reviewContentTextarea: Locator;
  readonly ratingInput: Locator;
  readonly isPublicCheckbox: Locator;
  readonly submitButton: Locator;
  readonly cancelButton: Locator;
  readonly successMessage: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page);

    // Initialize locators
    this.trackNameInput = page.getByLabel(/트랙|곡|track/i);
    this.albumNameInput = page.getByLabel(/앨범|album/i);
    this.artistNameInput = page.getByLabel(/아티스트|artist/i);
    this.reviewContentTextarea = page.getByLabel(/감상문|리뷰|review/i);
    this.ratingInput = page.getByLabel(/평점|rating/i);
    this.isPublicCheckbox = page.getByLabel(/공개|public/i);
    this.submitButton = page.getByRole('button', { name: /제출|등록|submit/i });
    this.cancelButton = page.getByRole('button', { name: /취소|cancel/i });
    this.successMessage = page.getByText(/성공|등록되었습니다|success/i);
    this.errorMessage = page.getByText(/오류|실패|error/i);
  }

  /**
   * Navigate to write review page
   */
  async goto() {
    await super.goto('/write-review');
  }

  /**
   * Fill in review form
   */
  async fillReviewForm(reviewData: {
    trackName: string;
    albumName: string;
    artistName: string;
    reviewContent: string;
    rating: number;
    isPublic: boolean;
  }) {
    await this.trackNameInput.fill(reviewData.trackName);
    await this.albumNameInput.fill(reviewData.albumName);
    await this.artistNameInput.fill(reviewData.artistName);
    await this.reviewContentTextarea.fill(reviewData.reviewContent);
    await this.ratingInput.fill(reviewData.rating.toString());

    if (reviewData.isPublic) {
      await this.isPublicCheckbox.check();
    } else {
      await this.isPublicCheckbox.uncheck();
    }
  }

  /**
   * Submit review form
   */
  async submitReview() {
    await this.submitButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Complete review submission workflow
   */
  async createReview(reviewData: {
    trackName: string;
    albumName: string;
    artistName: string;
    reviewContent: string;
    rating: number;
    isPublic: boolean;
  }) {
    await this.fillReviewForm(reviewData);
    await this.submitReview();
  }
}
