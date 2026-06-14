# Polling Baseline k6 Results

## Context

- Target API: `GET /api/user-reviews/{id}`
- Scenario: pending users repeatedly poll recommendation status.
- Polling interval: 3 seconds
- Test data: local fake PostgreSQL with 1,000 `PENDING` `user_reviews`
- Backend path: k6 -> Spring Boot -> local PostgreSQL
- FastAPI/Python was not included because this test measures status polling load, not recommendation processing.

## Commands

The executable examples are documented in `load-tests/polling-baseline.js`.

Common environment:

```bash
REVIEW_IDS="$(seq -s, 1 1000)"
BASE_URL=http://localhost:8080
REQUEST_TIMEOUT=5s
```

## Results

| Max VU | Total Requests | Avg RPS | Avg Latency | Median | Max Latency | p90 | p95 | Failure Rate | Notes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 500 | 11,231 | 73.74/s | 1.96 ms | 1.75 ms | 27.39 ms | 3.00 ms | 3.28 ms | 0.00% | Stable |
| 1,000 | 28,464 | 156.00/s | 1.87 ms | 1.64 ms | 37.55 ms | 2.79 ms | 3.22 ms | 0.00% | Stable |
| 6,000 | 175,368 | 961.36/s | 1.84 ms | 1.30 ms | 124.97 ms | 2.32 ms | 3.05 ms | 0.00% | Stable |

An earlier 200 VU run produced `p95=5.92ms` and `failure=0%`, but one request hung for `9m39s` before `REQUEST_TIMEOUT` was added. That run is excluded from the comparison table because the long request distorted average latency and total runtime.

## Interpretation

The polling status API was not a bottleneck in the local fake DB environment.

- 6,000 max VUs completed with `p95=3.05ms`.
- Failure rate stayed at `0.00%`.
- `iteration_duration` stayed close to the 3 second polling interval, so VUs were not meaningfully delayed by the backend.

This means the current single-review polling flow does not justify SSE on response-time grounds.

## SSE Decision Note

Based on this baseline, SSE should not be presented as a fix for an observed polling latency bottleneck in the current single-review flow.

Better decision framing:

- Keep polling for the current single-review recommendation flow because the API remains stable under the measured load.
- Consider SSE when the product expands to long-running multi-step workflows, such as playlist recommendation progress.
- Use SSE when the UX needs immediate progress/completion updates or when repeated polling becomes wasteful due to many state transitions.

## Portfolio Summary

```text
k6로 추천 상태 polling 기준선을 측정한 결과, 로컬 PostgreSQL fake DB 환경에서 6,000 VU까지 p95 3.05ms, 실패율 0%로 안정적이었다.
따라서 단건 추천 상태 조회에서는 polling이 즉각적인 성능 병목이 아니라고 판단했다.
SSE는 현재 구조의 병목 해결책이 아니라, 향후 플레이리스트 추천처럼 다단계 장기 작업의 진행률 push가 필요할 때 도입하는 전환 기준으로 정리했다.
```
