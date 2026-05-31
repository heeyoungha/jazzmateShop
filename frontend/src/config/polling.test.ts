import { describe, expect, it } from "vitest";
import {
  getRecommendationPollingInterval,
  RECOMMENDATION_POLLING_INTERVAL_MS,
} from "./polling";

describe("recommendation polling config", () => {
  it("설정된 폴링 인터벌을 반환한다", () => {
    expect(getRecommendationPollingInterval(0)).toBe(
      RECOMMENDATION_POLLING_INTERVAL_MS,
    );
    expect(getRecommendationPollingInterval(30_000)).toBe(
      RECOMMENDATION_POLLING_INTERVAL_MS,
    );
  });
});
