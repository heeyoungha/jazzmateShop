import { Music, User, Star, Calendar } from "lucide-react";

interface Review {
  id: number;
  trackName: string;
  artistName: string;
  rating?: number;
  createdAt: string;
}

interface ReviewCardProps {
  review: Review;
  onClick: () => void;
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function ReviewCard({ review, onClick }: ReviewCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left bg-white border rounded-xl p-5 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5 space-y-3"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1">
          <p className="flex items-center gap-1.5 font-semibold text-gray-900">
            <Music className="w-4 h-4 text-gray-400 shrink-0" />
            {review.trackName}
          </p>
          <p className="flex items-center gap-1.5 text-sm text-gray-500">
            <User className="w-3.5 h-3.5 shrink-0" />
            {review.artistName}
          </p>
        </div>
        {review.rating !== undefined && (
          <span className="flex items-center gap-1 text-sm font-medium text-yellow-500 shrink-0">
            <Star className="w-4 h-4 fill-yellow-400" />
            {review.rating}
          </span>
        )}
      </div>
      <p className="flex items-center gap-1.5 text-xs text-gray-400">
        <Calendar className="w-3.5 h-3.5" />
        {formatDate(review.createdAt)}
      </p>
    </button>
  );
}
