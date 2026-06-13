import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, PenLine } from "lucide-react";
import { ReviewCard } from "../components/ReviewCard";
import { getNextReviewPage } from "../lib/pagination";

interface UserReview {
  id: number;
  trackName: string;
  artistName: string;
  reviewContent: string;
  rating?: number;
  mood?: string;
  genre?: string;
  createdAt: string;
}

interface PageResponse {
  content: UserReview[];
  number: number;
  last: boolean;
}

type PageCursor = Pick<PageResponse, "number" | "last">;
const PAGE_SIZE = 10;

export function MyReviewsPage() {
  const navigate = useNavigate();
  const [reviews, setReviews] = useState<UserReview[]>([]);
  const [cursor, setCursor] = useState<PageCursor | null>(null);
  const loadingRef = useRef(false);
  const hasNoReviews =
    cursor?.number === 0 && cursor.last && reviews.length === 0;

  async function fetchPage(pageNum: number) {
    if (loadingRef.current) return;
    loadingRef.current = true;

    try {
      const res = await fetch(
        `/api/user-reviews?page=${pageNum}&size=${PAGE_SIZE}`,
      );
      const json: PageResponse = await res.json();

      setReviews((prev) => [...prev, ...json.content]);
      setCursor({ number: json.number, last: json.last });
    } finally {
      loadingRef.current = false;
    }
  }

  useEffect(() => {
    fetchPage(0);
  }, []);

  useEffect(() => {
    function handleScroll() {
      if (!cursor || cursor.last || loadingRef.current) return;
      if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
        const nextPage = getNextReviewPage(cursor);
        if (nextPage !== null) fetchPage(nextPage);
      }
    }
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [cursor]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              뒤로가기
            </button>
            <h1 className="text-2xl font-bold text-gray-900">AI 맞춤 추천</h1>
          </div>
          <button
            type="button"
            onClick={() => navigate("/write")}
            className="flex items-center gap-1.5 text-sm font-medium bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <PenLine className="w-4 h-4" />
            감상문 작성
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {hasNoReviews ? (
          <div className="flex flex-col items-center justify-center py-24 space-y-4 text-center">
            <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center">
              <PenLine className="w-7 h-7 text-gray-400" />
            </div>
            <p className="text-gray-500">아직 작성한 감상문이 없습니다.</p>
            <button
              type="button"
              onClick={() => navigate("/write")}
              className="text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
            >
              첫 감상문 작성하기 →
            </button>
          </div>
        ) : (
          <>
            <ul className="space-y-4">
              {reviews.map((r) => (
                <li key={r.id}>
                  <ReviewCard
                    review={r}
                    onClick={() => navigate(`/recommend/${r.id}`)}
                  />
                </li>
              ))}
            </ul>
            {cursor?.last && (
              <p className="text-center text-sm text-gray-400 mt-10">
                모든 감상문을 불러왔습니다.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
