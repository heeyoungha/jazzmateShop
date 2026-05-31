import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
    <ReviewForm onSubmit={handleSubmit} submitting={submitting} error={error} />
  );
}
