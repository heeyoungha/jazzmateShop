# Recommendation E2E k6 Results

## Context

- Target flow: `POST /api/user-reviews` -> polling `GET /api/user-reviews/{id}` until terminal status.
- Terminal statuses: `COMPLETED`, `FAILED`, timeout by `MAX_WAIT_SECONDS`.
- This test measures recommendation end-to-end latency, not only polling API capacity.

## Commands

### Start E2E Stack

`OPENAI_API_KEY`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` must be available from the shell or the root `.env`.

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml up --build
```

If Docker Compose does not auto-load the root `.env` in your shell, pass it explicitly:

```bash
docker compose --env-file .env -f load-tests/docker-compose.recommendation-e2e.yml up --build
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

## Result Table

| Mode | VU | Total Reviews | Completed | Failed | Timeout | submit p95 | time_to_completed p95 | time_to_completed p99 | Avg Polling Count | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Real OpenAI | 1 | 7 | 7 | 0 | 0 | 412.6 ms | 14.65 s | N/A | 3.29 | `completion_success_rate=100%`, `http_req_failed=0%` |
| Real OpenAI | 5 | 235 | 235 | 0 | 0 | 21.95 ms | 6.03 s | N/A | 1.28 | `completion_success_rate=100%`, `http_req_failed=0%` |
| Real OpenAI | 10 | 513 | 513 | 0 | 0 | 45.98 ms | 6.02 s | N/A | 1.17 | All thresholds passed, `http_req_failed=0%` |
| Mock OpenAI | 100 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Mock OpenAI | 500 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Mock OpenAI | 1000 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## Interpretation

Real OpenAI E2E smoke/small-load runs completed successfully up to 10 VUs.

- Completion success stayed at 100% for 1, 5, and 10 VUs.
- No recommendation failures, E2E timeouts, submit failures, polling failures, or HTTP request failures were observed.
- Polling remained lightweight: polling GET p95 stayed below 54 ms in all recorded runs and below 10 ms at 5/10 VUs.
- The observed `time_to_completed` p95 was about 6 seconds at 5/10 VUs. The 1 VU run was slower at 14.65 seconds, likely due to small sample size, cold start, or external API variance.

## Decision Note

The current evidence does not show polling as the bottleneck. The next high-load test should use an OpenAI/Supabase mock path so cost, rate limits, and external latency do not dominate Spring Boot/FastAPI/PostgreSQL structural measurements.
