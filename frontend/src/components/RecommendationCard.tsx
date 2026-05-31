interface Recommendation {
  id: number;
  userReviewId: number;
  albumId: number;
  recommendationReason: string;
}

interface RecommendationCardProps {
  recommendation: Recommendation;
}

export function RecommendationCard({
  recommendation,
}: RecommendationCardProps) {
  return (
    <div>
      <p>Album {recommendation.albumId}</p>
      <p>{recommendation.recommendationReason}</p>
    </div>
  );
}
