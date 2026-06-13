import { Disc3, Sparkles } from "lucide-react";

interface Recommendation {
  id: number;
  userReviewId: number;
  trackId: number;
  trackTitle: string;
  artistName: string;
  recommendationScore: number;
  recommendationReason: string;
}

interface RecommendationCardProps {
  recommendation: Recommendation;
  index: number;
}

export function RecommendationCard({
  recommendation,
  index,
}: RecommendationCardProps) {
  return (
    <div className="bg-white border rounded-xl p-6 space-y-3 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gray-900 text-white flex items-center justify-center text-sm font-bold shrink-0">
            {index + 1}
          </div>
          <div>
            <p className="flex items-center gap-1.5 text-sm font-semibold text-gray-900">
              <Disc3 className="w-4 h-4 text-gray-400" />
              {recommendation.trackTitle}
            </p>
            <p className="text-xs text-gray-400 pl-5">
              {recommendation.artistName}
            </p>
          </div>
        </div>
        {recommendation.recommendationScore !== undefined && (
          <span className="text-xs font-medium text-purple-600 bg-purple-50 px-2.5 py-1 rounded-full shrink-0">
            {(recommendation.recommendationScore * 100).toFixed(1)}% 일치
          </span>
        )}
      </div>
      <div className="flex gap-2 pl-12">
        <Sparkles className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
        <p className="text-sm text-gray-600 leading-relaxed">
          {recommendation.recommendationReason}
        </p>
      </div>
    </div>
  );
}
