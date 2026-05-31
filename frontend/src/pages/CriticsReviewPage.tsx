import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
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

  async function fetchPage(
    pageNum: number,
    ignore: () => boolean = () => false,
  ) {
    if (loadingRef.current) return;
    loadingRef.current = true;

    try {
      const res = await fetch(`/api/critics?page=${pageNum}`);

      if (!res.ok) {
        if (!ignore()) setError("전문가 리뷰 목록을 불러오지 못했습니다.");
        return;
      }

      const json = (await res.json()) as PageResponse;
      if (ignore()) return;

      setReviews((prev) => [...prev, ...json.content]);
      setCursor({ number: json.number, last: json.last });
      setError(null);
    } catch {
      if (!ignore()) setError("전문가 리뷰 목록을 불러오지 못했습니다.");
    } finally {
      loadingRef.current = false;
    }
  }

  useEffect(() => {
    let ignore = false;
    fetchPage(0, () => ignore);

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    function handleScroll() {
      if (!cursor || cursor.last || loadingRef.current) return;
      if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
        const nextPage = getNextCriticsPage(cursor);
        if (nextPage !== null) fetchPage(nextPage);
      }
    }
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [cursor]);

  if (error) {
    return <p>{error}</p>;
  }

  return (
    <ul>
      {reviews.map((r) => (
        <li key={r.id}>
          <CriticsReviewCard
            review={r}
            onClick={() => navigate(`/critics/${r.id}`)}
          />
        </li>
      ))}
    </ul>
  );
}
