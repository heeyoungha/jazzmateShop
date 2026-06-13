import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { CriticsReviewDetail } from "../components/CriticsReviewDetail";

interface CriticsDetail {
  id: string;
  title: string;
  reviewer: string;
  date: string;
  reviewSummary: string;
  content: string;
  url: string;
}

type PageState =
  | { status: "loading" }
  | { status: "success"; data: CriticsDetail }
  | { status: "notFound" }
  | { status: "error"; message: string };

export function CriticsReviewDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [state, setState] = useState<PageState>({ status: "loading" });

  useEffect(() => {
    let ignore = false;

    async function loadDetail() {
      if (!id) {
        setState({ status: "notFound" });
        return;
      }

      setState({ status: "loading" });

      try {
        const res = await fetch(`/api/critics/${id}`);

        if (res.status === 404) {
          if (!ignore) setState({ status: "notFound" });
          return;
        }

        if (!res.ok) {
          if (!ignore) {
            setState({
              status: "error",
              message: "전문가 리뷰를 불러오지 못했습니다.",
            });
          }
          return;
        }

        const json = (await res.json()) as CriticsDetail;
        if (!ignore) setState({ status: "success", data: json });
      } catch {
        if (!ignore) {
          setState({
            status: "error",
            message: "전문가 리뷰를 불러오지 못했습니다.",
          });
        }
      }
    }

    loadDetail();

    return () => {
      ignore = true;
    };
  }, [id]);

  const header = (
    <div className="bg-white shadow-sm border-b">
      <div className="max-w-3xl mx-auto px-4 py-5">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          전문가 리뷰 목록
        </button>
      </div>
    </div>
  );

  if (state.status === "loading") {
    return (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      </div>
    );
  }

  if (state.status === "notFound") {
    return (
      <div className="min-h-screen bg-gray-50">
        {header}
        <div className="flex justify-center py-16">
          <p className="text-gray-500">찾을 수 없는 페이지입니다.</p>
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

  return (
    <div className="min-h-screen bg-gray-50">
      {header}
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl border p-8 shadow-sm">
          <CriticsReviewDetail review={state.data} />
        </div>
      </div>
    </div>
  );
}
