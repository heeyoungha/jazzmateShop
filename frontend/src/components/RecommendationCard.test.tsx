import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { recommendation } from "../test/fixtures/api";
import { RecommendationCard } from "./RecommendationCard";

describe("RecommendationCard", () => {
  it("추천 카드 필드가 렌더링된다", () => {
    render(<RecommendationCard recommendation={recommendation} />);

    expect(
      screen.getByText(new RegExp(String(recommendation.albumId))),
    ).toBeInTheDocument();
    expect(
      screen.getByText("모달 재즈 특유의 정적인 분위기가 유사합니다."),
    ).toBeInTheDocument();
  });
});
