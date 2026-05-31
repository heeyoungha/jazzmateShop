import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { delayedCreateReviewHandler, requestLog } from "../test/msw/handlers";
import { server } from "../test/msw/server";
import { WriteReviewPage } from "./WriteReviewPage";

function renderWriteReviewPage() {
  return render(
    <MemoryRouter initialEntries={["/reviews/new"]}>
      <Routes>
        <Route path="/reviews/new" element={<WriteReviewPage />} />
        <Route path="/recommend/:id" element={<div>추천 페이지</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("곡명"), "So What");
  await user.type(screen.getByLabelText("아티스트"), "Miles Davis");
  await user.type(
    screen.getByLabelText("감상문"),
    "고요한 여백이 오래 남는다.",
  );
}

describe("WriteReviewPage", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("제출 중에는 저장 버튼이 비활성화된다", async () => {
    server.use(delayedCreateReviewHandler);
    const user = userEvent.setup();
    renderWriteReviewPage();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "저장" }));

    expect(screen.getByRole("button", { name: "저장 중" })).toBeDisabled();
  });

  it("제출 성공 시 추천 페이지로 이동한다", async () => {
    const user = userEvent.setup();
    renderWriteReviewPage();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "저장" }));

    expect(await screen.findByText("추천 페이지")).toBeInTheDocument();
    expect(requestLog.createReview).toBe(1);
  });

  it("400 오류 시 폼 에러 메시지가 표시된다", async () => {
    server.use(
      http.post("/api/user-reviews", () =>
        HttpResponse.json(
          { success: false, message: "trackName은 필수입니다." },
          { status: 400 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderWriteReviewPage();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "저장" }));

    expect(
      await screen.findByText("trackName은 필수입니다."),
    ).toBeInTheDocument();
  });

  it("500 오류 시 서버 에러 메시지가 표시된다", async () => {
    server.use(
      http.post("/api/user-reviews", () =>
        HttpResponse.json(
          { success: false, message: "서버 오류가 발생했습니다." },
          { status: 500 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderWriteReviewPage();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() => {
      expect(screen.getByText("서버 오류가 발생했습니다.")).toBeInTheDocument();
    });
  });

  it("네트워크 오류 시 일반 에러 메시지가 표시된다", async () => {
    server.use(http.post("/api/user-reviews", () => HttpResponse.error()));
    const user = userEvent.setup();
    renderWriteReviewPage();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "저장" }));

    expect(
      await screen.findByText("감상문 저장 중 오류가 발생했습니다."),
    ).toBeInTheDocument();
  });
});
