import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { criticsDetail } from "../test/fixtures/api";
import { CriticsReviewDetail } from "./CriticsReviewDetail";

describe("CriticsReviewDetail", () => {
  it("상세 필드가 렌더링된다", () => {
    render(<CriticsReviewDetail review={criticsDetail} />);

    // reviewSummary가 JSON이 아니면 content를 직접 렌더링한다
    expect(screen.getByText("전체 리뷰 본문입니다.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "원문 보기" })).toHaveAttribute(
      "href",
      "https://www.allaboutjazz.com/example",
    );
  });
});
