import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

// 200 VU:
// REVIEW_IDS="$(seq -s, 1 1000)" BASE_URL=http://localhost:8080 REQUEST_TIMEOUT=5s \
// RAMP_UP_VUS=50 HOLD_VUS=100 PRESSURE_VUS=200 \
// k6 run load-tests/polling-baseline.js
//
// 500 VU:
// REVIEW_IDS="$(seq -s, 1 1000)" BASE_URL=http://localhost:8080 REQUEST_TIMEOUT=5s \
// RAMP_UP_VUS=100 HOLD_VUS=300 PRESSURE_VUS=500 \
// k6 run load-tests/polling-baseline.js
//
// 1000 VU:
// REVIEW_IDS="$(seq -s, 1 1000)" BASE_URL=http://localhost:8080 REQUEST_TIMEOUT=5s \
// RAMP_UP_VUS=200 HOLD_VUS=500 PRESSURE_VUS=1000 PRESSURE_DURATION=1m \
// k6 run load-tests/polling-baseline.js
//
// 2000 VU stress:
// REVIEW_IDS="$(seq -s, 1 1000)" BASE_URL=http://localhost:8080 REQUEST_TIMEOUT=5s \
// RAMP_UP_VUS=500 HOLD_VUS=1000 PRESSURE_VUS=2000 PRESSURE_DURATION=1m \
// k6 run load-tests/polling-baseline.js
//
// 4000 VU stress:
// REVIEW_IDS="$(seq -s, 1 1000)" BASE_URL=http://localhost:8080 REQUEST_TIMEOUT=5s \
// RAMP_UP_VUS=1000 HOLD_VUS=2000 PRESSURE_VUS=4000 PRESSURE_DURATION=1m \
// k6 run load-tests/polling-baseline.js
//
// 6000 VU stress:
// REVIEW_IDS="$(seq -s, 1 1000)" BASE_URL=http://localhost:8080 REQUEST_TIMEOUT=5s \
// RAMP_UP_VUS=1500 HOLD_VUS=3000 PRESSURE_VUS=6000 PRESSURE_DURATION=1m \
// k6 run load-tests/polling-baseline.js

const baseUrl = __ENV.BASE_URL || "http://localhost:8080";
const pollingIntervalSeconds = Number(__ENV.POLLING_INTERVAL_SECONDS || "3");
const requestTimeout = __ENV.REQUEST_TIMEOUT || "5s";
const setupReviewCount = Number(__ENV.SETUP_REVIEW_COUNT || "0");
const reviewIdsFromEnv = (__ENV.REVIEW_IDS || "")
  .split(",")
  .map((id) => Number(id.trim()))
  .filter((id) => Number.isInteger(id) && id > 0);

const pollingDuration = new Trend("polling_get_duration", true);
const pollingFailures = new Rate("polling_get_failed");
const completedResponses = new Counter("polling_completed_responses");
const pendingResponses = new Counter("polling_pending_responses");
const failedResponses = new Counter("polling_failed_responses");

export const options = {
  scenarios: {
    polling_users: {
      executor: "ramping-vus",
      stages: [
        { duration: __ENV.RAMP_UP_DURATION || "30s", target: Number(__ENV.RAMP_UP_VUS || "50") },
        { duration: __ENV.HOLD_DURATION || "1m", target: Number(__ENV.HOLD_VUS || "100") },
        { duration: __ENV.PRESSURE_DURATION || "30s", target: Number(__ENV.PRESSURE_VUS || "200") },
        { duration: __ENV.RAMP_DOWN_DURATION || "30s", target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    polling_get_failed: ["rate<0.01"],
    polling_get_duration: ["p(95)<500", "p(99)<1000"],
  },
};

export function setup() {
  if (reviewIdsFromEnv.length > 0) {
    return { reviewIds: reviewIdsFromEnv };
  }

  if (setupReviewCount <= 0) {
    throw new Error("Set REVIEW_IDS=1,2,3 or SETUP_REVIEW_COUNT to create PENDING reviews before the run.");
  }

  const reviewIds = [];
  for (let i = 0; i < setupReviewCount; i += 1) {
    const res = http.post(
      `${baseUrl}/api/user-reviews`,
      JSON.stringify({
        trackName: `Polling Load Test Track ${i + 1}`,
        artistName: "Jazzmate Load Test",
        reviewContent: "A spacious modal performance with a warm bass line and restrained cymbal texture.",
        rating: 4.5,
        mood: "calm",
        genre: "jazz",
        energyLevel: 0.55,
        bpm: 96,
        vocalStyle: "instrumental",
        instrumentation: "piano, bass, drums",
        isPublic: false,
      }),
      { headers: { "Content-Type": "application/json" } },
    );

    check(res, {
      "created review": (r) => r.status === 201,
    });

    if (res.status !== 201) {
      throw new Error(`Failed to create setup review: status=${res.status}, body=${res.body}`);
    }

    const body = JSON.parse(res.body);
    reviewIds.push(body.data.id);
  }

  return { reviewIds };
}

export default function (data) {
  const reviewIds = data.reviewIds;
  const reviewId = reviewIds[Math.floor(Math.random() * reviewIds.length)];
  const res = http.get(`${baseUrl}/api/user-reviews/${reviewId}`, {
    timeout: requestTimeout,
  });

  pollingDuration.add(res.timings.duration);
  pollingFailures.add(res.status !== 200);

  const ok = check(res, {
    "status 200": (r) => r.status === 200,
    "has recommendationStatus": (r) => {
      try {
        return JSON.parse(r.body).recommendationStatus !== undefined;
      } catch {
        return false;
      }
    },
  });

  if (ok && res.status === 200) {
    const body = JSON.parse(res.body);
    if (body.recommendationStatus === "PENDING") pendingResponses.add(1);
    if (body.recommendationStatus === "COMPLETED") completedResponses.add(1);
    if (body.recommendationStatus === "FAILED") failedResponses.add(1);
  }

  sleep(pollingIntervalSeconds);
}
