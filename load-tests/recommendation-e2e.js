import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

// Real OpenAI smoke:
// BASE_URL=http://localhost:8080 REQUEST_TIMEOUT=30s POLLING_INTERVAL_SECONDS=3 \
// MAX_WAIT_SECONDS=180 VUS=1 DURATION=1m \
// k6 run load-tests/recommendation-e2e.js
//
// Real OpenAI small load:
// BASE_URL=http://localhost:8080 REQUEST_TIMEOUT=30s POLLING_INTERVAL_SECONDS=3 \
// MAX_WAIT_SECONDS=180 VUS=5 DURATION=3m \
// k6 run load-tests/recommendation-e2e.js
//
// Mock OpenAI structural load:
// BASE_URL=http://localhost:8080 REQUEST_TIMEOUT=10s POLLING_INTERVAL_SECONDS=1 \
// MAX_WAIT_SECONDS=60 VUS=100 DURATION=5m \
// k6 run load-tests/recommendation-e2e.js

const baseUrl = __ENV.BASE_URL || "http://localhost:8080";
const requestTimeout = __ENV.REQUEST_TIMEOUT || "30s";
const pollingIntervalSeconds = Number(__ENV.POLLING_INTERVAL_SECONDS || "3");
const maxWaitSeconds = Number(__ENV.MAX_WAIT_SECONDS || "180");
const minCompletionSuccessRate = __ENV.MIN_COMPLETION_SUCCESS_RATE || "0.95";
const maxSubmitP95Ms = __ENV.MAX_SUBMIT_P95_MS || "1000";
const maxPollingP95Ms = __ENV.MAX_POLLING_P95_MS || "500";
const maxTimeToCompletedP95Ms = __ENV.MAX_TIME_TO_COMPLETED_P95_MS || String(maxWaitSeconds * 1000);
const disableThresholds = (__ENV.DISABLE_THRESHOLDS || "false").toLowerCase() === "true";

const submitDuration = new Trend("submit_api_duration", true);
const pollingDuration = new Trend("polling_get_duration", true);
const timeToCompleted = new Trend("time_to_completed", true);
const pollingCountPerReview = new Trend("polling_count_per_review");

const submitFailures = new Rate("submit_api_failed");
const pollingFailures = new Rate("polling_get_failed");
const completionSuccessRate = new Rate("completion_success_rate");
const recommendationFailedRate = new Rate("recommendation_failed_rate");
const e2eTimeoutRate = new Rate("e2e_timeout_rate");
const e2eFailedRate = new Rate("e2e_failed_rate");

const submittedReviews = new Counter("submitted_reviews");
const completedReviews = new Counter("completed_reviews");
const failedReviews = new Counter("failed_reviews");
const timedOutReviews = new Counter("timed_out_reviews");
const pendingResponses = new Counter("pending_responses");

const thresholds = disableThresholds
  ? {}
  : {
      http_req_failed: ["rate<0.05"],
      submit_api_failed: ["rate<0.01"],
      polling_get_failed: ["rate<0.01"],
      submit_api_duration: [`p(95)<${maxSubmitP95Ms}`],
      polling_get_duration: [`p(95)<${maxPollingP95Ms}`],
      time_to_completed: [`p(95)<${maxTimeToCompletedP95Ms}`],
      completion_success_rate: [`rate>${minCompletionSuccessRate}`],
      e2e_failed_rate: ["rate<0.05"],
    };

export const options = {
  scenarios: {
    recommendation_e2e_users: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || "1"),
      duration: __ENV.DURATION || "1m",
      gracefulStop: __ENV.GRACEFUL_STOP || "3m",
    },
  },
  thresholds,
};

function buildReviewPayload() {
  const uniqueId = `${__VU}-${__ITER}-${Date.now()}`;

  return {
    trackName: `Recommendation E2E Track ${uniqueId}`,
    artistName: "Jazzmate Load Test",
    reviewContent:
      "A spacious modal jazz performance with a warm bass line, restrained cymbal texture, and a calm late-night atmosphere.",
    rating: 4.5,
    mood: "calm",
    genre: "modal jazz",
    energyLevel: 0.55,
    bpm: 96,
    vocalStyle: "instrumental",
    instrumentation: "piano, bass, drums",
    isPublic: false,
  };
}

function parseJson(body) {
  try {
    return JSON.parse(body);
  } catch {
    return null;
  }
}

function recordTerminalFailure({ failedByStatus = false, timedOut = false } = {}) {
  completionSuccessRate.add(false);
  recommendationFailedRate.add(failedByStatus);
  e2eTimeoutRate.add(timedOut);
  e2eFailedRate.add(true);
}

export default function () {
  const startedAt = Date.now();

  const submit = http.post(`${baseUrl}/api/user-reviews`, JSON.stringify(buildReviewPayload()), {
    headers: { "Content-Type": "application/json" },
    timeout: requestTimeout,
  });

  submitDuration.add(submit.timings.duration);
  submitFailures.add(submit.status !== 201);

  const submitBody = parseJson(submit.body);
  const submitted = check(submit, {
    "submit status 201": (r) => r.status === 201,
    "submit has review id": () => Number.isInteger(submitBody?.data?.id),
  });

  if (!submitted) {
    recordTerminalFailure();
    return;
  }

  submittedReviews.add(1);

  const reviewId = submitBody.data.id;
  let pollCount = 0;

  while (Date.now() - startedAt < maxWaitSeconds * 1000) {
    sleep(pollingIntervalSeconds);
    pollCount += 1;

    const poll = http.get(`${baseUrl}/api/user-reviews/${reviewId}`, {
      timeout: requestTimeout,
    });

    pollingDuration.add(poll.timings.duration);
    pollingFailures.add(poll.status !== 200);

    const pollBody = parseJson(poll.body);
    check(poll, {
      "poll status 200": (r) => r.status === 200,
      "poll has recommendationStatus": () => pollBody?.recommendationStatus !== undefined,
    });

    if (poll.status !== 200 || pollBody?.recommendationStatus === undefined) {
      continue;
    }

    const status = pollBody.recommendationStatus;

    if (status === "PENDING") {
      pendingResponses.add(1);
      continue;
    }

    pollingCountPerReview.add(pollCount);

    if (status === "COMPLETED") {
      completedReviews.add(1);
      timeToCompleted.add(Date.now() - startedAt);
      completionSuccessRate.add(true);
      recommendationFailedRate.add(false);
      e2eTimeoutRate.add(false);
      e2eFailedRate.add(false);
      return;
    }

    if (status === "FAILED") {
      failedReviews.add(1);
      recordTerminalFailure({ failedByStatus: true });
      return;
    }

    recordTerminalFailure();
    return;
  }

  timedOutReviews.add(1);
  pollingCountPerReview.add(pollCount);
  recordTerminalFailure({ timedOut: true });
}
