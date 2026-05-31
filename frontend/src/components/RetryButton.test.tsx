import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RetryButton } from "./RetryButton";

describe("RetryButton", () => {
  it("클릭하면 onRetry가 호출된다", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(<RetryButton onRetry={onRetry} />);

    await user.click(screen.getByRole("button", { name: "다시 시도" }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
