import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, Music, User, FileText, Loader2 } from "lucide-react";
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
  albumId: string;
  albumTitle?: string | null;
  albumArtist?: string | null;
  criticsReviewId: string | null;
  criticsReviewUrl: string | null;
  recommendationScore: number;
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
  const navigate = useNavigate();
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

  const header = (
    <div className="bg-white shadow-sm border-b">
      <div className="max-w-3xl mx-auto px-4 py-5">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />내 감상문 목록
        </button>
      </div>
    </div>
  );

  if (state.status === "loading") {
    return (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="flex justify-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </div>
    );
  }

  if (state.status === "notFound") {
    return (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="flex justify-center py-16">
          <p className="text-gray-500">감상문을 찾을 수 없습니다.</p>
        </div>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="flex justify-center py-16">
          <p className="text-gray-500">{state.message}</p>
        </div>
      </div>
    );
  }

  const { data } = state;

  if (data.recommendationStatus === "PENDING") {
    return (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="max-w-3xl mx-auto px-4 py-12 flex flex-col items-center gap-4 text-center">
          <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
          <p className="text-lg font-medium text-gray-700">
            AI가 추천을 준비하고 있습니다...
          </p>
          <p className="text-sm text-gray-400">
            감상문을 분석해 어울리는 앨범을 찾고 있어요. 잠시만 기다려주세요.
          </p>
        </div>
      </div>
    );
  }

  if (data.recommendationStatus === "FAILED") {
    return (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="max-w-3xl mx-auto px-4 py-12 flex flex-col items-center gap-4 text-center">
          <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center">
            <span className="text-2xl">😢</span>
          </div>
          <p className="text-lg font-medium text-gray-700">
            추천 생성에 실패했습니다.
          </p>
          {state.retryError && (
            <p className="text-sm text-red-500">{state.retryError}</p>
          )}
          <RetryButton onRetry={handleRetry} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {header}
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        {/* 내 감상문 */}
        <div className="bg-white rounded-xl border shadow-sm p-6 space-y-3">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
            내 감상문
          </h2>
          <div className="flex items-center gap-4 text-sm text-gray-700">
            <span className="flex items-center gap-1.5 font-semibold">
              <Music className="w-4 h-4 text-gray-400" />
              {data.review.trackName}
            </span>
            <span className="flex items-center gap-1.5 text-gray-500">
              <User className="w-4 h-4 text-gray-400" />
              {data.review.artistName}
            </span>
          </div>
          <div className="flex gap-2">
            <FileText className="w-4 h-4 text-gray-300 shrink-0 mt-0.5" />
            <p className="text-sm text-gray-600 leading-relaxed">
              {data.review.reviewContent}
            </p>
          </div>
        </div>

        {/* 추천 결과 */}
        <div className="space-y-3">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest px-1">
            AI 추천 앨범{" "}
            {data.recommendations.length > 0 &&
              `(${data.recommendations.length})`}
          </h2>
          {data.recommendations.length === 0 ? (
            <p className="text-center text-sm text-gray-400 py-12">
              추천 결과가 없습니다.
            </p>
          ) : (
            <ul className="space-y-3">
              {data.recommendations.map((rec, i) => (
                <li key={rec.id}>
                  <RecommendationCard recommendation={rec} index={i} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
