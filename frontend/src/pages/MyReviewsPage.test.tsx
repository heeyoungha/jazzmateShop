import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { userReviewPage } from "../test/fixtures/api";
import { lastUserReviewsPageHandler, requestLog } from "../test/msw/handlers";
import { server } from "../test/msw/server";
import { MyReviewsPage } from "./MyReviewsPage";

const firstReview = userReviewPage({ number: 0 }).content[0];
const secondReview = userReviewPage({ number: 1 }).content[0];

function renderMyReviewsPage() {
  return render(
    <MemoryRouter initialEntries={["/reviews"]}>
      <Routes>
        <Route path="/reviews" element={<MyReviewsPage />} />
        <Route path="/recommend/:id" element={<div>AI 맞춤 추천 결과</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function scrollToBottom() {
  act(() => {
    window.dispatchEvent(new Event("scroll"));
  });
}

describe("MyReviewsPage", () => {
  it("마운트 시 첫 페이지를 조회한다", async () => {
    renderMyReviewsPage();

    await screen.findByText(firstReview.trackName);

    expect(requestLog.userReviewPages).toEqual([0]);
  });

  it("목록 응답 시 리뷰 카드가 렌더링된다", async () => {
    renderMyReviewsPage();

    expect(await screen.findByText(firstReview.trackName)).toBeInTheDocument();
    expect(screen.getByText(firstReview.artistName)).toBeInTheDocument();
  });

  it("목록이 비어있으면 빈 상태 메시지가 표시된다", async () => {
    server.use(
      http.get("/api/user-reviews", () =>
        HttpResponse.json({
          content: [],
          totalElements: 0,
          totalPages: 0,
          number: 0,
          size: 10,
          last: true,
        }),
      ),
    );

    renderMyReviewsPage();

    expect(
      await screen.findByText("작성한 감상문이 없습니다."),
    ).toBeInTheDocument();
  });

  it("마지막 페이지가 아닐 때 스크롤 하단 도달 시 다음 페이지를 조회한다", async () => {
    renderMyReviewsPage();

    await screen.findByText(firstReview.trackName);
    scrollToBottom();

    await waitFor(() => expect(requestLog.userReviewPages).toEqual([0, 1]));
  });

  it("마지막 페이지일 때 스크롤 하단 도달 시 추가 조회하지 않는다", async () => {
    server.use(lastUserReviewsPageHandler);
    renderMyReviewsPage();

    await screen.findByText(firstReview.trackName);
    scrollToBottom();

    await new Promise((r) => setTimeout(r, 100));
    expect(requestLog.userReviewPages).toEqual([0]);
  });

  it("다음 페이지 조회 시 기존 목록에 이어서 추가된다", async () => {
    renderMyReviewsPage();

    await screen.findByText(firstReview.trackName);
    scrollToBottom();

    expect(await screen.findByText(secondReview.trackName)).toBeInTheDocument();
    expect(screen.getByText(firstReview.trackName)).toBeInTheDocument();
  });

  it("카드 클릭 시 AI 맞춤 추천 결과 페이지로 이동한다", async () => {
    const user = userEvent.setup();
    renderMyReviewsPage();

    await user.click(await screen.findByRole("button", { name: /So What/ }));

    expect(await screen.findByText("AI 맞춤 추천 결과")).toBeInTheDocument();
  });
});
