import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RECOMMENDATION_POLLING_INTERVAL_MS } from "../config/polling";
import {
  failedHandler,
  pendingOnlyHandler,
  pendingThenCompletedHandler,
  requestLog,
} from "../test/msw/handlers";
import { recommendation, review, REVIEW_ID } from "../test/fixtures/api";
import { server } from "../test/msw/server";
import { ReviewBasedRecommendPage } from "./ReviewBasedRecommendPage";

function renderRecommendPage() {
  return render(
    <MemoryRouter initialEntries={[`/recommend/${REVIEW_ID}`]}>
      <Routes>
        <Route path="/recommend/:id" element={<ReviewBasedRecommendPage />} />
        <Route path="/elsewhere" element={<div>다른 페이지</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ReviewBasedRecommendPage", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("마운트 시 리뷰 상세를 조회한다", async () => {
    renderRecommendPage();

    await screen.findByText(new RegExp(String(recommendation.albumId)));

    expect(requestLog.reviewDetail).toBe(1);
  });

  it("pending 상태이면 대기 메시지를 표시하고 폴링을 계속한다", async () => {
    vi.useFakeTimers();
    server.use(pendingOnlyHandler);
    renderRecommendPage();

    expect(
      await screen.findByText("추천을 준비하고 있습니다."),
    ).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(RECOMMENDATION_POLLING_INTERVAL_MS);
    });

    await waitFor(() => expect(requestLog.reviewDetail).toBe(2));
  });

  it("completed 상태이면 추천 목록을 렌더링하고 폴링을 중단한다", async () => {
    vi.useFakeTimers();
    server.use(pendingThenCompletedHandler);
    renderRecommendPage();

    expect(
      await screen.findByText("추천을 준비하고 있습니다."),
    ).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(RECOMMENDATION_POLLING_INTERVAL_MS);
    });

    // 기준 감상문
    expect(await screen.findByText(review.trackName)).toBeInTheDocument();
    expect(screen.getByText(review.artistName)).toBeInTheDocument();
    expect(screen.getByText(review.reviewContent)).toBeInTheDocument();
    // 추천 곡 목록
    expect(
      screen.getByText(new RegExp(String(recommendation.albumId))),
    ).toBeInTheDocument();
    expect(
      screen.getByText(recommendation.recommendationReason),
    ).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(RECOMMENDATION_POLLING_INTERVAL_MS);
    });

    expect(requestLog.reviewDetail).toBe(2);
  });

  it("failed 상태이면 다시 시도 버튼을 표시하고 폴링을 중단한다", async () => {
    vi.useFakeTimers();
    server.use(failedHandler);
    renderRecommendPage();

    expect(
      await screen.findByText("추천 생성에 실패했습니다."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "다시 시도" }),
    ).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(RECOMMENDATION_POLLING_INTERVAL_MS);
    });

    expect(requestLog.reviewDetail).toBe(1);
  });

  it("failed 상태에서 자동으로 재시도하지 않는다", async () => {
    server.use(failedHandler);
    renderRecommendPage();

    expect(
      await screen.findByText("추천 생성에 실패했습니다."),
    ).toBeInTheDocument();
    expect(requestLog.retry).toBe(0);
  });

  it("다시 시도 클릭 시 retry 요청을 보내고 폴링을 재시작한다", async () => {
    vi.useFakeTimers();
    server.use(failedHandler);
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderRecommendPage();

    await screen.findByText("추천 생성에 실패했습니다.");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));

    expect(requestLog.retry).toBe(1);
    expect(screen.getByText("추천을 준비하고 있습니다.")).toBeInTheDocument();
  });

  it("언마운트 시 폴링 타이머가 제거된다", async () => {
    vi.useFakeTimers();
    server.use(pendingOnlyHandler);
    const { unmount } = renderRecommendPage();

    await screen.findByText("추천을 준비하고 있습니다.");
    unmount();

    await act(async () => {
      vi.advanceTimersByTime(RECOMMENDATION_POLLING_INTERVAL_MS);
    });

    expect(requestLog.reviewDetail).toBe(1);
  });
});
