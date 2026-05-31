import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { RecommendationCard } from "../components/RecommendationCard";
import { RetryButton } from "../components/RetryButton";
import { getRecommendationPollingInterval as getPollingDelay } from "../config/polling";

interface ReviewDetail {
  id: number;
  trackName: string;
  artistName: string;
  reviewContent: string;
}

interface Recommendation {
  id: number;
  userReviewId: number;
  albumId: number;
  recommendationReason: string;
}

interface ReviewResponse {
  review: ReviewDetail;
  recommendationStatus: "PENDING" | "COMPLETED" | "FAILED";
  recommendations: Recommendation[];
}

type PageState =
  | { status: "loading" }
  | { status: "success"; data: ReviewResponse; retryError?: string }
  | { status: "notFound" }
  | { status: "error"; message: string };

export function ReviewBasedRecommendPage() {
  const { id } = useParams<{ id: string }>();
  const [state, setState] = useState<PageState>({ status: "loading" });
  const startedAt = useRef(Date.now());
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollingControllerRef = useRef<AbortController | null>(null);

  async function fetchDetail(signal: AbortSignal) {
    try {
      const res = await fetch(`/api/user-reviews/${id}`, { signal });

      if (res.status === 404) {
        setState({ status: "notFound" });
        return null;
      }

      if (!res.ok) {
        setState({
          status: "error",
          message: "추천 결과를 불러오지 못했습니다.",
        });
        return null;
      }

      const json: ReviewResponse = await res.json();
      setState({ status: "success", data: json });
      return json;
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return null;
      }

      setState({
        status: "error",
        message: "추천 결과를 불러오지 못했습니다.",
      });
      return null;
    }
  }

  async function startPolling(signal: AbortSignal) {
    const result = await fetchDetail(signal);
    if (result?.recommendationStatus === "PENDING") {
      const elapsed = Date.now() - startedAt.current;
      timerRef.current = setTimeout(
        () => startPolling(signal),
        getPollingDelay(elapsed),
      );
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    pollingControllerRef.current = controller;
    startPolling(controller.signal);

    return () => {
      controller.abort();
      if (timerRef.current) clearTimeout(timerRef.current);
      if (pollingControllerRef.current === controller) {
        pollingControllerRef.current = null;
      }
    };
  }, [id]);

  async function handleRetry() {
    const signal = pollingControllerRef.current?.signal;
    if (!signal) return;

    let res: Response;
    try {
      res = await fetch(`/api/user-reviews/${id}/retry`, {
        method: "POST",
        signal,
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      setState((prev) =>
        prev.status === "success"
          ? {
              ...prev,
              retryError: "추천 재시도를 시작하지 못했습니다.",
            }
          : prev,
      );
      return;
    }

    if (!res.ok) {
      setState((prev) =>
        prev.status === "success"
          ? {
              ...prev,
              retryError: "추천 재시도를 시작하지 못했습니다.",
            }
          : prev,
      );
      return;
    }

    startedAt.current = Date.now();
    setState((prev) =>
      prev.status === "success"
        ? {
            status: "success",
            data: { ...prev.data, recommendationStatus: "PENDING" },
          }
        : prev,
    );
    startPolling(signal);
  }

  if (state.status === "loading") return null;

  if (state.status === "notFound") {
    return <p>감상문을 찾을 수 없습니다.</p>;
  }

  if (state.status === "error") {
    return <p>{state.message}</p>;
  }

  const { data } = state;

  if (data.recommendationStatus === "PENDING") {
    return <p>추천을 준비하고 있습니다.</p>;
  }

  if (data.recommendationStatus === "FAILED") {
    return (
      <div>
        <p>추천 생성에 실패했습니다.</p>
        {state.retryError && <p>{state.retryError}</p>}
        <RetryButton onRetry={handleRetry} />
      </div>
    );
  }

  return (
    <div>
      <div>
        <p>{data.review.trackName}</p>
        <p>{data.review.artistName}</p>
        <p>{data.review.reviewContent}</p>
      </div>
      <ul>
        {data.recommendations.map((rec) => (
          <li key={rec.id}>
            <RecommendationCard recommendation={rec} />
          </li>
        ))}
      </ul>
    </div>
  );
}
