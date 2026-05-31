import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
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

  if (state.status === "notFound") {
    return <p>찾을 수 없는 페이지입니다.</p>;
  }

  if (state.status === "error") {
    return <p>{state.message}</p>;
  }

  if (state.status === "loading") return null;

  return <CriticsReviewDetail review={state.data} />;
}
