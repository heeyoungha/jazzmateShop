import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { criticsPage } from "../test/fixtures/api";
import { lastCriticsPageHandler, requestLog } from "../test/msw/handlers";
import { server } from "../test/msw/server";
import { CriticsReviewPage } from "./CriticsReviewPage";

const firstCritics = criticsPage({ number: 0 }).content[0];

function renderCriticsReviewPage() {
  return render(
    <MemoryRouter initialEntries={["/critics"]}>
      <Routes>
        <Route path="/critics" element={<CriticsReviewPage />} />
        <Route path="/critics/:id" element={<div>전문가 리뷰 상세</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function scrollToBottom() {
  act(() => {
    window.dispatchEvent(new Event("scroll"));
  });
}

describe("CriticsReviewPage", () => {
  it("마운트 시 첫 페이지를 조회한다", async () => {
    renderCriticsReviewPage();

    await screen.findByText(firstCritics.title);

    expect(requestLog.criticsPages).toEqual([0]);
  });

  it("목록 응답 시 전문가 리뷰 카드가 렌더링된다", async () => {
    renderCriticsReviewPage();

    expect(await screen.findByText(firstCritics.title)).toBeInTheDocument();
    expect(screen.getByText(firstCritics.reviewer)).toBeInTheDocument();
  });

  it("마지막 페이지가 아닐 때 스크롤 하단 도달 시 다음 페이지를 조회한다", async () => {
    renderCriticsReviewPage();

    await screen.findByText(firstCritics.title);
    scrollToBottom();

    await waitFor(() => expect(requestLog.criticsPages).toEqual([0, 1]));
  });

  it("마지막 페이지일 때 스크롤 하단 도달 시 추가 조회하지 않는다", async () => {
    server.use(lastCriticsPageHandler);
    renderCriticsReviewPage();

    await screen.findByText(firstCritics.title);
    scrollToBottom();

    await new Promise((r) => setTimeout(r, 100));
    expect(requestLog.criticsPages).toEqual([0]);
  });

  it("목록 조회 중 서버 오류가 발생하면 일반 에러 메시지가 표시된다", async () => {
    server.use(
      http.get("/api/critics", () =>
        HttpResponse.json(
          { success: false, message: "서버 오류가 발생했습니다." },
          { status: 500 },
        ),
      ),
    );

    renderCriticsReviewPage();

    expect(
      await screen.findByText("전문가 리뷰 목록을 불러오지 못했습니다."),
    ).toBeInTheDocument();
  });

  it("목록 조회 중 네트워크 오류가 발생하면 일반 에러 메시지가 표시된다", async () => {
    server.use(http.get("/api/critics", () => HttpResponse.error()));

    renderCriticsReviewPage();

    expect(
      await screen.findByText("전문가 리뷰 목록을 불러오지 못했습니다."),
    ).toBeInTheDocument();
  });

  it("카드 클릭 시 전문가 리뷰 상세 페이지로 이동한다", async () => {
    const user = userEvent.setup();
    renderCriticsReviewPage();

    await user.click(
      await screen.findByRole("button", { name: /Kind of Blue Review/ }),
    );

    expect(await screen.findByText("전문가 리뷰 상세")).toBeInTheDocument();
  });
});
