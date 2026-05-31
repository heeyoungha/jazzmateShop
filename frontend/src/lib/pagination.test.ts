import { describe, expect, it } from "vitest";
import { getNextCriticsPage, getNextReviewPage } from "./pagination";

describe("pagination helpers", () => {
  it("리뷰 - 마지막 페이지가 아니면 다음 페이지 번호를 반환한다", () => {
    expect(getNextReviewPage({ number: 0, last: false })).toBe(1);
  });

  it("리뷰 - 마지막 페이지이면 null을 반환한다", () => {
    expect(getNextReviewPage({ number: 0, last: true })).toBeNull();
  });

  it("전문가 리뷰 - 마지막 페이지가 아니면 다음 페이지 번호를 반환한다", () => {
    expect(getNextCriticsPage({ number: 2, last: false })).toBe(3);
  });

  it("전문가 리뷰 - 마지막 페이지이면 null을 반환한다", () => {
    expect(getNextCriticsPage({ number: 2, last: true })).toBeNull();
  });
});
