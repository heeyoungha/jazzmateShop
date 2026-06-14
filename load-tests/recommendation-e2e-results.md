# Recommendation E2E k6 Results

## Context

- Target flow: `POST /api/user-reviews` -> polling `GET /api/user-reviews/{id}` until terminal status.
- Terminal statuses: `COMPLETED`, `FAILED`, timeout by `MAX_WAIT_SECONDS`.
- This test measures recommendation end-to-end latency, not only polling API capacity.

## Commands

### Start Mock E2E Stack

The default compose path uses the load-test mock AI API, so OpenAI and Supabase credentials are not required.

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml up --build
```

Optional mock latency controls:

```bash
MOCK_EMBEDDING_DELAY_MS=300 \
MOCK_REASON_DELAY_MS=700 \
docker compose -f load-tests/docker-compose.recommendation-e2e.yml up --build
```

### Real OpenAI Smoke

```bash
BASE_URL=http://localhost:8080 \
REQUEST_TIMEOUT=30s \
POLLING_INTERVAL_SECONDS=3 \
MAX_WAIT_SECONDS=180 \
VUS=1 \
DURATION=1m \
k6 run load-tests/recommendation-e2e.js
```

### Real OpenAI Small Load

```bash
BASE_URL=http://localhost:8080 \
REQUEST_TIMEOUT=30s \
POLLING_INTERVAL_SECONDS=3 \
MAX_WAIT_SECONDS=180 \
VUS=5 \
DURATION=3m \
k6 run load-tests/recommendation-e2e.js
```

### Mock OpenAI Structural Load

```bash
BASE_URL=http://localhost:8080 \
REQUEST_TIMEOUT=10s \
POLLING_INTERVAL_SECONDS=1 \
MAX_WAIT_SECONDS=60 \
VUS=100 \
DURATION=5m \
k6 run load-tests/recommendation-e2e.js
```

### Mock OpenAI Ramping Structural Load

Use ramping runs when testing 500+ VUs so initial connection spikes do not dominate the measurement.

```bash
BASE_URL=http://localhost:8080 \
REQUEST_TIMEOUT=10s \
POLLING_INTERVAL_SECONDS=1 \
MAX_WAIT_SECONDS=60 \
LOAD_PROFILE=ramping \
RAMP_UP_DURATION=1m \
RAMP_UP_VUS=100 \
HOLD_DURATION=5m \
HOLD_VUS=500 \
RAMP_DOWN_DURATION=30s \
k6 run load-tests/recommendation-e2e.js
```

## Result Table

| Mode | VU | Total Reviews | Completed | Failed | Timeout | submit p95 | time_to_completed p95 | time_to_completed p99 | Avg Polling Count | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Real OpenAI | 1 | 7 | 7 | 0 | 0 | 412.6 ms | 14.65 s | N/A | 3.29 | `completion_success_rate=100%`, `http_req_failed=0%` |
| Real OpenAI | 5 | 235 | 235 | 0 | 0 | 21.95 ms | 6.03 s | N/A | 1.28 | `completion_success_rate=100%`, `http_req_failed=0%` |
| Real OpenAI | 10 | 513 | 513 | 0 | 0 | 45.98 ms | 6.02 s | N/A | 1.17 | All thresholds passed, `http_req_failed=0%` |
| Mock OpenAI | 100 | 14,606 | 14,606 | 0 | 0 | 92.27 ms | 2.11 s | N/A | 2.00 | `48.45 reviews/s`, all thresholds passed |
| Mock OpenAI | 500 ramping | 25,888 | 25,888 | 0 | 0 | 2.05 s | 7.15 s | N/A | 2.26 | `66.19 reviews/s`, success 100%, latency thresholds crossed |
| Mock OpenAI | 1000 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

Note: an initial 500 `constant-vus` run produced startup `connection reset by peer` errors on `POST /api/user-reviews`. Re-run 500+ VU measurements with the ramping profile to separate cold-start/instant-spike behavior from sustained throughput.

## Interpretation

Real OpenAI E2E smoke/small-load runs completed successfully up to 10 VUs.

- Completion success stayed at 100% for 1, 5, and 10 VUs.
- No recommendation failures, E2E timeouts, submit failures, polling failures, or HTTP request failures were observed.
- Polling remained lightweight: polling GET p95 stayed below 54 ms in all recorded runs and below 10 ms at 5/10 VUs.
- The observed `time_to_completed` p95 was about 6 seconds at 5/10 VUs. The 1 VU run was slower at 14.65 seconds, likely due to small sample size, cold start, or external API variance.
- With the mock AI path at 100 VUs, the Spring Boot/FastAPI/PostgreSQL structure completed 14,606 reviews in 5 minutes with no failures and `time_to_completed p95=2.11s`.
- With the mock AI path ramped to 500 VUs, all 25,888 submitted reviews completed successfully, but submit and polling latency degraded sharply: `submit_api_duration p95=2.05s`, `polling_get_duration p95=1.82s`. This marks the first measured saturation signal in the local structural test.

## Decision Note

The current evidence does not show polling as a bottleneck at low or moderate load. Under the mock 500 VU structural test, the system still completed all requests, but both submit and polling latency crossed thresholds, so the next investigation should focus on Spring Boot/PostgreSQL connection pool, Tomcat thread, async callback, and local Docker resource limits before testing 1,000 VUs.
