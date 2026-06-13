import { act, fireEvent, render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RECOMMENDATION_POLLING_INTERVAL_MS } from "../config/polling";
import {
  failedHandler,
  failedThenPendingAfterRetryHandler,
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

async function advanceTimers(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("ReviewBasedRecommendPage", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("마운트 시 리뷰 상세를 조회한다", async () => {
    renderRecommendPage();

    await screen.findByText(recommendation.albumTitle);

    expect(requestLog.reviewDetail).toBe(1);
  });

  it("pending 상태이면 대기 메시지를 표시하고 폴링을 계속한다", async () => {
    vi.useFakeTimers();
    server.use(pendingOnlyHandler);
    renderRecommendPage();

    await advanceTimers(0);

    expect(screen.getByText(/추천을 준비하고 있습니다/)).toBeInTheDocument();

    await advanceTimers(RECOMMENDATION_POLLING_INTERVAL_MS);

    expect(requestLog.reviewDetail).toBe(2);
  });

  it("completed 상태이면 추천 목록을 렌더링하고 폴링을 중단한다", async () => {
    vi.useFakeTimers();
    server.use(pendingThenCompletedHandler);
    renderRecommendPage();

    await advanceTimers(0);

    expect(screen.getByText(/추천을 준비하고 있습니다/)).toBeInTheDocument();

    await advanceTimers(RECOMMENDATION_POLLING_INTERVAL_MS);

    // 기준 감상문
    expect(screen.getByText(review.trackName)).toBeInTheDocument();
    expect(screen.getAllByText(review.artistName)).not.toHaveLength(0);
    expect(screen.getByText(review.reviewContent)).toBeInTheDocument();
    // 추천 곡 목록
    expect(screen.getByText(recommendation.albumTitle)).toBeInTheDocument();
    expect(screen.getAllByText(recommendation.albumArtist)).not.toHaveLength(0);
    expect(
      screen.getByText(recommendation.recommendationReason),
    ).toBeInTheDocument();

    await advanceTimers(RECOMMENDATION_POLLING_INTERVAL_MS);

    expect(requestLog.reviewDetail).toBe(2);
  });

  it("failed 상태이면 다시 시도 버튼을 표시하고 폴링을 중단한다", async () => {
    vi.useFakeTimers();
    server.use(failedHandler);
    renderRecommendPage();

    await advanceTimers(0);

    expect(screen.getByText("추천 생성에 실패했습니다.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "다시 시도" }),
    ).toBeInTheDocument();

    await advanceTimers(RECOMMENDATION_POLLING_INTERVAL_MS);

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

  it("감상문을 찾을 수 없으면 not found 메시지를 표시한다", async () => {
    server.use(
      http.get("/api/user-reviews/:id", () =>
        HttpResponse.json(
          { success: false, message: "감상문을 찾을 수 없습니다." },
          { status: 404 },
        ),
      ),
    );

    renderRecommendPage();

    expect(
      await screen.findByText("감상문을 찾을 수 없습니다."),
    ).toBeInTheDocument();
  });

  it("리뷰 상세 조회 실패 시 오류 메시지를 표시한다", async () => {
    server.use(
      http.get("/api/user-reviews/:id", () =>
        HttpResponse.json(
          { success: false, message: "서버 오류가 발생했습니다." },
          { status: 500 },
        ),
      ),
    );

    renderRecommendPage();

    expect(
      await screen.findByText("추천 결과를 불러오지 못했습니다."),
    ).toBeInTheDocument();
  });

  it("다시 시도 클릭 시 retry 요청을 보내고 폴링을 재시작한다", async () => {
    vi.useFakeTimers();
    server.use(failedThenPendingAfterRetryHandler);
    renderRecommendPage();

    await advanceTimers(0);

    screen.getByText("추천 생성에 실패했습니다.");
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    });

    expect(requestLog.retry).toBe(1);
    await advanceTimers(0);
    expect(screen.getByText(/추천을 준비하고 있습니다/)).toBeInTheDocument();
  });

  it("retry 요청 실패 시 failed 화면에 머물고 오류 메시지를 표시한다", async () => {
    vi.useFakeTimers();
    server.use(
      failedHandler,
      http.post("/api/user-reviews/:id/retry", () => {
        requestLog.retry += 1;
        return HttpResponse.json(
          { success: false, message: "재시도 실패" },
          { status: 500 },
        );
      }),
    );
    renderRecommendPage();

    await advanceTimers(0);

    screen.getByText("추천 생성에 실패했습니다.");
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    });

    expect(requestLog.retry).toBe(1);
    expect(
      screen.getByText("추천 재시도를 시작하지 못했습니다."),
    ).toBeInTheDocument();

    await advanceTimers(RECOMMENDATION_POLLING_INTERVAL_MS);

    expect(requestLog.reviewDetail).toBe(1);
  });

  it("언마운트 시 폴링 타이머가 제거된다", async () => {
    vi.useFakeTimers();
    server.use(pendingOnlyHandler);
    const { unmount } = renderRecommendPage();

    await advanceTimers(0);
    screen.getByText(/추천을 준비하고 있습니다/);
    unmount();

    await advanceTimers(RECOMMENDATION_POLLING_INTERVAL_MS);

    expect(requestLog.reviewDetail).toBe(1);
  });
});
