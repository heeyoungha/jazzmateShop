import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { CriticsReviewCard } from "../components/CriticsReviewCard";
import { getNextCriticsPage } from "../lib/pagination";

interface CriticsReview {
  id: string;
  title: string;
  reviewer: string;
  date: string;
  reviewSummary: string;
}

interface PageResponse {
  content: CriticsReview[];
  number: number;
  last: boolean;
}

type PageCursor = Pick<PageResponse, "number" | "last">;

export function CriticsReviewPage() {
  const navigate = useNavigate();
  const [reviews, setReviews] = useState<CriticsReview[]>([]);
  const [cursor, setCursor] = useState<PageCursor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loadingRef = useRef(false);
  const cursorRef = useRef<PageCursor | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  async function fetchPage(pageNum: number) {
    if (loadingRef.current) return;
    loadingRef.current = true;

    try {
      const res = await fetch(`/api/critics?page=${pageNum}`);
      if (!res.ok) {
        setError("전문가 리뷰 목록을 불러오지 못했습니다.");
        return;
      }
      const json = (await res.json()) as PageResponse;
      setReviews((prev) => [...prev, ...json.content]);
      cursorRef.current = { number: json.number, last: json.last };
      setCursor({ number: json.number, last: json.last });
      setError(null);
    } catch {
      setError("전문가 리뷰 목록을 불러오지 못했습니다.");
    } finally {
      loadingRef.current = false;
    }
  }

  useEffect(() => {
    fetchPage(0);
  }, []);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0].isIntersecting) return;
        const cur = cursorRef.current;
        if (!cur || cur.last || loadingRef.current) return;
        const nextPage = getNextCriticsPage(cur);
        if (nextPage !== null) fetchPage(nextPage);
      },
      { rootMargin: "200px" },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">{error}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-5 flex items-center gap-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            뒤로가기
          </button>
          <h1 className="text-2xl font-bold text-gray-900">전문가 리뷰</h1>
        </div>
      </div>

      {/* 목록 */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {reviews.length === 0 ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          </div>
        ) : (
          <ul className="space-y-4">
            {reviews.map((r) => (
              <li key={r.id}>
                <CriticsReviewCard
                  review={r}
                  onClick={() => navigate(`/critics/${r.id}`)}
                />
              </li>
            ))}
          </ul>
        )}

        <div ref={sentinelRef} className="h-1" />

        {cursor?.last && reviews.length > 0 && (
          <p className="text-center text-sm text-gray-400 mt-10">
            모든 리뷰를 불러왔습니다.
          </p>
        )}
      </div>
    </div>
  );
}
