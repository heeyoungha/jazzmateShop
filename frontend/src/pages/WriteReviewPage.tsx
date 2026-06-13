import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { ReviewForm, type ReviewFormData } from "../components/ReviewForm";

interface CreateReviewResponse {
  id: number;
}

interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export function WriteReviewPage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | undefined>();

  async function handleSubmit(data: ReviewFormData) {
    setSubmitting(true);
    setError(undefined);

    try {
      const res = await fetch("/api/user-reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const json = (await res.json()) as ApiResponse<CreateReviewResponse>;

      if (!res.ok) {
        setError(json.message || "감상문 저장에 실패했습니다.");
        return;
      }

      if (!json.success || typeof json.data?.id !== "number") {
        setError(json.message || "감상문 저장에 실패했습니다.");
        return;
      }

      navigate(`/recommend/${json.data.id}`);
    } catch {
      setError("감상문 저장 중 오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-2xl mx-auto px-4 py-5 flex items-center gap-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            뒤로가기
          </button>
          <h1 className="text-2xl font-bold text-gray-900">감상문 작성</h1>
        </div>
      </div>
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl border shadow-sm p-8">
          <ReviewForm
            onSubmit={handleSubmit}
            submitting={submitting}
            error={error}
          />
        </div>
      </div>
    </div>
  );
}
