import { render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { criticsDetail, CRITICS_ID } from "../test/fixtures/api";
import { requestLog } from "../test/msw/handlers";
import { server } from "../test/msw/server";
import { CriticsReviewDetailPage } from "./CriticsReviewDetailPage";

function renderCriticsReviewDetailPage() {
  return render(
    <MemoryRouter initialEntries={[`/critics/${CRITICS_ID}`]}>
      <Routes>
        <Route path="/critics/:id" element={<CriticsReviewDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CriticsReviewDetailPage", () => {
  it("마운트 시 전문가 리뷰 상세를 조회한다", async () => {
    renderCriticsReviewDetailPage();

    expect(await screen.findByText(criticsDetail.content)).toBeInTheDocument();

    expect(requestLog.criticsDetail).toBe(1);
  });

  it("상세 조회 시 상세 뷰가 표시된다", async () => {
    renderCriticsReviewDetailPage();

    expect(await screen.findByText(criticsDetail.content)).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "원문 보기" })).toHaveAttribute(
      "href",
      criticsDetail.url,
    );
  });

  it("상세 조회 결과가 없으면 에러 페이지가 표시된다", async () => {
    server.use(
      http.get("/api/critics/:id", () =>
        HttpResponse.json(
          { success: false, message: "전문가 리뷰를 찾을 수 없습니다." },
          { status: 404 },
        ),
      ),
    );

    renderCriticsReviewDetailPage();

    expect(
      await screen.findByText("찾을 수 없는 페이지입니다."),
    ).toBeInTheDocument();
  });
});
