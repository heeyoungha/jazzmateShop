import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { recommendation } from "../test/fixtures/api";
import { RecommendationCard } from "./RecommendationCard";

describe("RecommendationCard", () => {
  it("추천 카드 필드가 렌더링된다", () => {
    render(
      <MemoryRouter>
        <RecommendationCard recommendation={recommendation} index={0} />
      </MemoryRouter>,
    );

    expect(screen.getByText(recommendation.albumTitle)).toBeInTheDocument();
    expect(screen.getByText(recommendation.albumArtist)).toBeInTheDocument();
    expect(
      screen.getByText("모달 재즈 특유의 정적인 분위기가 유사합니다."),
    ).toBeInTheDocument();
  });
});
