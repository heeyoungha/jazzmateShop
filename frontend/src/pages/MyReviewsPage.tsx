import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
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

  if (hasNoReviews) {
    return <p>작성한 감상문이 없습니다.</p>;
  }

  return (
    <ul>
      {reviews.map((r) => (
        <li key={r.id}>
          <ReviewCard
            review={r}
            onClick={() => navigate(`/recommend/${r.id}`)}
          />
        </li>
      ))}
    </ul>
  );
}
