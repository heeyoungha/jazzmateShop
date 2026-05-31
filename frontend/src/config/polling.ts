export const RECOMMENDATION_POLLING_INTERVAL_MS = 3_000;

export function getRecommendationPollingInterval(_elapsedMs: number): number {
  return RECOMMENDATION_POLLING_INTERVAL_MS;
}
