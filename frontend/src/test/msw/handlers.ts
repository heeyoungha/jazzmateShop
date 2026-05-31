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

  http.get("/api/user-reviews", ({ request }) => {
    const page = Number(new URL(request.url).searchParams.get("page") ?? 0);
    requestLog.userReviewPages.push(page);
    return HttpResponse.json(userReviewPage({ number: page, last: page >= 1 }));
  }),

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
