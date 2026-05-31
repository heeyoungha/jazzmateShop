import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { criticsPage } from "../test/fixtures/api";
import { CriticsReviewCard } from "./CriticsReviewCard";

describe("CriticsReviewCard", () => {
  const review = criticsPage().content[0];

  it("카드 요약 필드가 렌더링된다", () => {
    render(<CriticsReviewCard review={review} onClick={vi.fn()} />);

    expect(screen.getByText("Kind of Blue Review")).toBeInTheDocument();
    expect(screen.getByText("All About Jazz")).toBeInTheDocument();
    expect(screen.getByText("2026-05-23")).toBeInTheDocument();
    expect(screen.getByText(/정교한 앙상블/)).toBeInTheDocument();
  });

  it("클릭하면 onClick이 호출된다", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<CriticsReviewCard review={review} onClick={onClick} />);

    await user.click(
      screen.getByRole("button", { name: /Kind of Blue Review/ }),
    );

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
