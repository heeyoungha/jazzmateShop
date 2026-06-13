import { Calendar, User } from "lucide-react";

interface CriticsReview {
  id: string;
  title: string;
  reviewer: string;
  date: string;
  reviewSummary: string;
}

interface CriticsReviewCardProps {
  review: CriticsReview;
  onClick: () => void;
}

function parseSummary(raw: string): string | null {
  if (!raw?.trim()) return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed?.summary?.korean ?? null;
  } catch {
    return null;
  }
}

function formatDate(dateString: string) {
  if (!dateString) return "";
  return new Date(dateString).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function CriticsReviewCard({ review, onClick }: CriticsReviewCardProps) {
  const summary = parseSummary(review.reviewSummary);

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left bg-white border rounded-xl p-6 hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5 space-y-3"
    >
      <h3 className="text-lg font-semibold text-gray-900 leading-snug">
        {review.title}
      </h3>

      <div className="flex items-center gap-4 text-sm text-gray-500">
        <span className="flex items-center gap-1">
          <User className="w-3.5 h-3.5" />
          {review.reviewer}
        </span>
        {review.date && (
          <span className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            {formatDate(review.date)}
          </span>
        )}
      </div>

      {summary && (
        <p className="text-sm text-gray-600 leading-relaxed line-clamp-3 bg-blue-50 px-4 py-3 rounded-lg">
          {summary}
        </p>
      )}
    </button>
  );
}
