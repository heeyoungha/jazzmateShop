import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { userReviewPage } from "../test/fixtures/api";
import { ReviewCard } from "./ReviewCard";

describe("ReviewCard", () => {
  const review = userReviewPage().content[0];

  it("요약 필드가 렌더링된다", () => {
    render(<ReviewCard review={review} onClick={vi.fn()} />);

    expect(screen.getByText("So What")).toBeInTheDocument();
    expect(screen.getByText("Miles Davis")).toBeInTheDocument();
    expect(screen.getByText("4.5")).toBeInTheDocument();
    expect(screen.getByText("2026-05-23T10:00:00")).toBeInTheDocument();
  });

  it("평점이 없으면 평점 영역을 렌더링하지 않는다", () => {
    const reviewWithoutRating = { ...review, rating: undefined };

    render(<ReviewCard review={reviewWithoutRating} onClick={vi.fn()} />);

    expect(screen.queryByText("4.5")).not.toBeInTheDocument();
    expect(screen.getByText("2026-05-23T10:00:00")).toBeInTheDocument();
  });

  it("클릭하면 onClick이 호출된다", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<ReviewCard review={review} onClick={onClick} />);

    await user.click(screen.getByRole("button", { name: /So What/ }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
