import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { criticsDetail } from "../test/fixtures/api";
import { CriticsReviewDetail } from "./CriticsReviewDetail";

describe("CriticsReviewDetail", () => {
  it("상세 필드가 렌더링된다", () => {
    render(<CriticsReviewDetail review={criticsDetail} />);

    expect(screen.getByText("전체 리뷰 본문입니다.")).toBeInTheDocument();
    expect(
      screen.getByText("정교한 앙상블과 절제된 긴장감이 돋보이는 리뷰입니다."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "원문 보기" })).toHaveAttribute(
      "href",
      "https://www.allaboutjazz.com/example",
    );
  });
});
