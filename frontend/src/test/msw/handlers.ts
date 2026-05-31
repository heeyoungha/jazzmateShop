import { delay, http, HttpResponse } from "msw";
import {
  completedReviewDetail,
  criticsDetail,
  criticsPage,
  failedReviewDetail,
  pendingReviewDetail,
  REVIEW_ID,
  userReviewPage,
} from "../fixtures/api";

export const requestLog = {
  createReview: 0,
  reviewDetail: 0,
  retry: 0,
  userReviewPages: [] as number[],
  criticsPages: [] as number[],
  criticsDetail: 0,
  reset() {
    this.createReview = 0;
    this.reviewDetail = 0;
    this.retry = 0;
    this.userReviewPages = [];
    this.criticsPages = [];
    this.criticsDetail = 0;
  },
};

// 감상문 목록을 첫 페이지부터 마지막 페이지로 강제하는 테스트용 핸들러.
export const lastUserReviewsPageHandler = http.get("/api/user-reviews", ({ request }) => {
  const searchParams = new URL(request.url).searchParams;
  const page = Number(searchParams.get("page") ?? 0);
  const size = Number(searchParams.get("size") ?? 0);
  requestLog.userReviewPages.push(page);
  return HttpResponse.json(userReviewPage({ number: page, last: true }));
});

// 전문가 리뷰 목록을 첫 페이지부터 마지막 페이지로 강제하는 테스트용 핸들러.
export const lastCriticsPageHandler = http.get("/api/critics", ({ request }) => {
  const page = Number(new URL(request.url).searchParams.get("page") ?? 0);
  requestLog.criticsPages.push(page);
  return HttpResponse.json(criticsPage({ number: page, last: true }));
});

export const defaultHandlers = [
  http.post("/api/user-reviews", async () => {
    requestLog.createReview += 1;
    return HttpResponse.json(
      {
        success: true,
        message: "감상문이 저장되었습니다.",
        data: { id: REVIEW_ID },
      },
      { status: 201 },
    );
  }),

  http.get("/api/user-reviews/:id", () => {
    requestLog.reviewDetail += 1;
    return HttpResponse.json(completedReviewDetail);
  }),

  http.post("/api/user-reviews/:id/retry", () => {
    requestLog.retry += 1;
    return HttpResponse.json({
      success: true,
      message: "추천 재시도를 시작했습니다.",
      data: null,
    });
  }),

  // 기본 감상문 목록 핸들러: page 쿼리를 기록하고 page 1부터 마지막 페이지로 응답한다.
  http.get("/api/user-reviews", ({ request }) => {
    const searchParams = new URL(request.url).searchParams;
    const page = Number(searchParams.get("page") ?? 0);
    const size = Number(searchParams.get("size") ?? 0);
    requestLog.userReviewPages.push(page);
    return HttpResponse.json(userReviewPage({ number: page, last: page >= 1 }));
  }),

  // 기본 전문가 리뷰 목록 핸들러: page 쿼리를 기록하고 page 1부터 마지막 페이지로 응답한다.
  http.get("/api/critics", ({ request }) => {
    const page = Number(new URL(request.url).searchParams.get("page") ?? 0);
    requestLog.criticsPages.push(page);
    return HttpResponse.json(criticsPage({ number: page, last: page >= 1 }));
  }),

  http.get("/api/critics/:id", () => {
    requestLog.criticsDetail += 1;
    return HttpResponse.json(criticsDetail);
  }),
];

export const pendingThenCompletedHandler = http.get(
  "/api/user-reviews/:id",
  () => {
    requestLog.reviewDetail += 1;
    return HttpResponse.json(
      requestLog.reviewDetail === 1
        ? pendingReviewDetail
        : completedReviewDetail,
    );
  },
);

export const pendingOnlyHandler = http.get("/api/user-reviews/:id", () => {
  requestLog.reviewDetail += 1;
  return HttpResponse.json(pendingReviewDetail);
});

export const failedHandler = http.get("/api/user-reviews/:id", () => {
  requestLog.reviewDetail += 1;
  return HttpResponse.json(failedReviewDetail);
});

export const failedThenPendingAfterRetryHandler = http.get(
  "/api/user-reviews/:id",
  () => {
    requestLog.reviewDetail += 1;
    return HttpResponse.json(
      requestLog.retry === 0 ? failedReviewDetail : pendingReviewDetail,
    );
  },
);

export const delayedCreateReviewHandler = http.post(
  "/api/user-reviews",
  async () => {
    requestLog.createReview += 1;
    await delay(100);
    return HttpResponse.json(
      {
        success: true,
        message: "감상문이 저장되었습니다.",
        data: { id: REVIEW_ID },
      },
      { status: 201 },
    );
  },
);
