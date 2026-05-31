import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReviewForm } from "./ReviewForm";

describe("ReviewForm", () => {
  it("필수 필드가 렌더링된다", () => {
    render(<ReviewForm onSubmit={vi.fn()} />);

    expect(screen.getByLabelText("곡명")).toBeInTheDocument();
    expect(screen.getByLabelText("아티스트")).toBeInTheDocument();
    expect(screen.getByLabelText("감상문")).toBeInTheDocument();
  });

  it("선택 필드가 렌더링된다", () => {
    render(<ReviewForm onSubmit={vi.fn()} />);

    expect(screen.getByLabelText("평점")).toBeInTheDocument();
    expect(screen.getByLabelText("무드")).toBeInTheDocument();
    expect(screen.getByLabelText("장르")).toBeInTheDocument();
    expect(screen.getByLabelText("에너지")).toBeInTheDocument();
    expect(screen.getByLabelText("BPM")).toBeInTheDocument();
    expect(screen.getByLabelText("보컬 스타일")).toBeInTheDocument();
    expect(screen.getByLabelText("편성")).toBeInTheDocument();
    expect(screen.getByLabelText("공개")).toBeInTheDocument();
  });

  it("필수 필드 없이 제출하면 유효성 에러가 표시된다", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<ReviewForm onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: "저장" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText("곡명은 필수입니다.")).toBeInTheDocument();
    expect(screen.getByText("아티스트는 필수입니다.")).toBeInTheDocument();
    expect(screen.getByText("감상문은 필수입니다.")).toBeInTheDocument();
  });

  it("선택 필드 없이도 제출이 가능하다", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<ReviewForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText("곡명"), "So What");
    await user.type(screen.getByLabelText("아티스트"), "Miles Davis");
    await user.type(
      screen.getByLabelText("감상문"),
      "고요한 여백이 오래 남는다.",
    );
    await user.click(screen.getByRole("button", { name: "저장" }));

    expect(onSubmit).toHaveBeenCalledWith({
      trackName: "So What",
      artistName: "Miles Davis",
      reviewContent: "고요한 여백이 오래 남는다.",
      isPublic: false,
    });
  });

  it("선택 필드를 포함하면 해당 값이 onSubmit에 전달된다", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<ReviewForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText("곡명"), "So What");
    await user.type(screen.getByLabelText("아티스트"), "Miles Davis");
    await user.type(
      screen.getByLabelText("감상문"),
      "차분한 모달 재즈의 인상이 강하다.",
    );
    await user.type(screen.getByLabelText("평점"), "4.5");
    await user.type(screen.getByLabelText("무드"), "calm");
    await user.type(screen.getByLabelText("장르"), "modal jazz");
    await user.type(screen.getByLabelText("에너지"), "0.3");
    await user.type(screen.getByLabelText("BPM"), "120");
    await user.type(screen.getByLabelText("보컬 스타일"), "instrumental");
    await user.type(screen.getByLabelText("편성"), "quintet");
    await user.click(screen.getByLabelText("공개"));
    await user.click(screen.getByRole("button", { name: "저장" }));

    expect(onSubmit).toHaveBeenCalledWith({
      trackName: "So What",
      artistName: "Miles Davis",
      reviewContent: "차분한 모달 재즈의 인상이 강하다.",
      rating: 4.5,
      mood: "calm",
      genre: "modal jazz",
      energyLevel: 0.3,
      bpm: 120,
      vocalStyle: "instrumental",
      instrumentation: "quintet",
      isPublic: true,
    });
  });
});
