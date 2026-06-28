# 추천 E2E k6 결과

## 문서 위치와 기록 원칙

- 상세 결과/명령/해석: `load-tests/recommendation-e2e-results.md`
- k6 raw summary: `load-tests/*summary.json`
- Grafana/Prometheus 캡처: `load-tests/monitoring/`
- 로드맵 요약: `docs/고도화.md`

`docs/고도화.md`에는 결론과 링크만 남기고, 실행 명령/표/로그 해석은 이 문서에 누적한다.

## 측정 맥락

- 대상 흐름: `POST /api/user-reviews` -> `GET /api/user-reviews/{id}` polling -> terminal status 확인
- 종료 상태: `COMPLETED`, `FAILED`, `MAX_WAIT_SECONDS` 초과 timeout
- 목적: polling API 단독 성능이 아니라, 감상문 제출부터 추천 완료 확인까지의 end-to-end 지연 시간을 측정한다.

---

## 개인화/클러스터링 적용 후 측정

MusicBrainz 메타 재순위와 개인화 클러스터링 로직이 붙은 뒤, SSE 전환 필요성을 판단하기 위해 측정했다.

### 측정 모드 구분

| 모드 | FastAPI 앱 | OpenAI | 추천 DB 조회 | Spring 저장 DB | 목적 |
|---|---|---|---|---|---|
| Mock AI E2E | mock FastAPI | mock | 사용 안 함 | local PostgreSQL | Spring submit/callback/polling 구조 한계 확인 |
| Real FastAPI E2E | 실제 `app.main:app` | real | 실제 Supabase | local PostgreSQL | 실제 외부 API 포함 소량 smoke |
| DB Real + OpenAI Mock | 실제 `app.main:app` | mock | 실제 Supabase | local PostgreSQL | GPT 비용 제거 후 실제 추천 DB 조회 경로의 고동시성 한계 확인 |

**모드별 스택 차이가 결과 해석에 중요하다.**

Mock AI E2E는 embedding 생성, Supabase pgvector 검색, 개인화 클러스터링을 전혀 실행하지 않는다. 지연 시간만 시뮬레이션하고 고정 응답을 callback으로 보내는 단순한 mock 서버다. 따라서 500 VU에서 22,000건 이상이 전부 완료된 것은 "실제 추천 파이프라인이 500 VU를 버틴다"는 근거가 아니다. Spring submit/callback/polling 구조 자체의 처리 여력을 확인한 것이다.

DB Real + OpenAI Mock은 실제 FastAPI가 Supabase pgvector 검색, 메타데이터 재순위, 클러스터링을 전부 실행한다. 추천 1건당 처리 비용이 Mock AI와 비교할 수 없이 크기 때문에, 같은 VU 수에서도 유입 속도를 따라가지 못하고 PENDING이 쌓이기 시작한다.

### 사용한 파일

```text
load-tests/recommendation-e2e.js
load-tests/docker-compose.recommendation-real.yml
load-tests/docker-compose.recommendation-db-real-openai-mock.yml
backendPython/app/main.py
backendPython/app/core/config.py
```

`recommendation-e2e.js`는 `REVIEW_POOL_SIZE=1000` 기본값으로 1000개 감상문 mock pool을 순환한다. 감상문 생성은 외부 API를 호출하지 않는다.

`MOCK_OPENAI=true`일 때 FastAPI는 실제 서비스/Repository/Rerank 경로를 사용하되, OpenAI embedding/chat client만 fake client로 대체한다. 따라서 DB Real + OpenAI Mock 테스트는 GPT 비용 없이 실제 Supabase 조회 경로를 압박한다.

### Real FastAPI E2E 소량 측정

실제 FastAPI와 실제 OpenAI/Supabase를 모두 사용했다. 비용과 rate limit 위험 때문에 1/5/10 VU, 30초로 제한했다.

```bash
BASE_URL=http://localhost:18080 \
REQUEST_TIMEOUT=60s \
POLLING_INTERVAL_SECONDS=3 \
MAX_WAIT_SECONDS=180 \
VUS=10 \
DURATION=30s \
k6 run --summary-export=load-tests/recommendation-real-10vu-summary.json \
load-tests/recommendation-e2e.js
```

| VU | duration | submitted | completed | success rate | submit p95 | polling p95 | time_to_completed p95 | timeout |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30s | 6 | 6 | 100% | 214.57 ms | 88.30 ms | 10.86 s | 0 |
| 5 | 30s | 36 | 36 | 100% | 18.59 ms | 14.23 ms | 6.80 s | 0 |
| 10 | 30s | 51 | 51 | 100% | 30.18 ms | 17.96 ms | 6.05 s | 0 |

해석:

- 실제 FastAPI/OpenAI/Supabase 경로는 10 VU 소량 부하까지 실패 없이 완료됐다.
- submit/polling API 자체는 낮은 지연을 유지했다.
- 추천 완료 p95는 약 6초 수준이었다.
- 이 결과만으로는 polling이 병목이라고 볼 근거가 없다.

### DB Real + OpenAI Mock 1000 VU 측정

이 테스트는 GPT API만 mock하고, FastAPI의 실제 추천 서비스/Repository/Rerank 경로와 실제 Supabase DB 조회를 사용했다.

실행 전 1 VU smoke:

```bash
BASE_URL=http://localhost:18080 \
REQUEST_TIMEOUT=60s \
POLLING_INTERVAL_SECONDS=3 \
MAX_WAIT_SECONDS=180 \
REVIEW_POOL_SIZE=1000 \
VUS=1 \
DURATION=15s \
k6 run --summary-export=load-tests/recommendation-db-real-openai-mock-1vu-summary.json \
load-tests/recommendation-e2e.js
```

1 VU smoke 결과:

| VU | duration | submitted | completed | success rate | submit p95 | polling p95 | time_to_completed p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 15s | 5 | 5 | 100% | 236.28 ms | 104.02 ms | 3.34 s |

1000 VU ramping:

```bash
BASE_URL=http://localhost:18080 \
REQUEST_TIMEOUT=60s \
POLLING_INTERVAL_SECONDS=3 \
MAX_WAIT_SECONDS=180 \
REVIEW_POOL_SIZE=1000 \
LOAD_PROFILE=ramping \
RAMP_UP_DURATION=1m \
RAMP_UP_VUS=500 \
HOLD_DURATION=1m \
HOLD_VUS=1000 \
RAMP_DOWN_DURATION=30s \
k6 run --summary-export=load-tests/recommendation-db-real-openai-mock-1000vu-summary.json \
load-tests/recommendation-e2e.js
```

1000 VU 결과:

| 항목 | 값 |
|---|---:|
| submitted_reviews | 1,374 |
| completed_reviews | 374 |
| completion coverage | 27.2% |
| interrupted iterations | 1,000 |
| pending_responses | 34,067 |
| polling_count_per_review p95 | 13 |
| submit p95 | 10.40 ms |
| polling p95 | 5.20 ms |
| time_to_completed p95 | 39.05 s |
| time_to_completed max | 48.06 s |
| HTTP failure rate | 0% |

주의:

- k6의 `completion_success_rate=100%`는 terminal result까지 도달한 374건 안에서 실패가 없었다는 뜻이다.
- 전체 제출 1,374건 중 완료된 것은 374건뿐이므로, 핵심 지표는 `completion coverage=27.2%`, `interrupted iterations=1,000`, `PENDING 누적`이다.

테스트 종료 직후 local Spring DB 상태:

```text
COMPLETED: 446
PENDING:   1,933
```

이 값에는 사전 seed 데이터와 1 VU smoke 결과가 함께 포함되어 있다. 핵심은 테스트 종료 뒤에도 `PENDING`이 대량으로 남았다는 점이다.

FastAPI 로그에서 확인된 오류:

```text
httpx.ConnectTimeout
app.core.exceptions.CallbackError
Spring callback failed
```

Grafana 캡처: `load-tests/monitoring/개인화클러스터링/스크린샷 2026-06-28 오후 9.53.37.png`

| 패널 | 관측 |
|---|---|
| Completion Coverage | 21:45부터 28%로 급락 후 수평 — 제출은 계속 들어오는데 완료가 멈춘 시점이 명확함 |
| 제출/완료 누적 | submitted 1,400까지 상승, completed 390에서 수평 — 격차가 PENDING 적체를 직접 보여줌 |
| HTTP Request Rate | `/api/user-reviews/{id}` polling이 300 req/s까지 폭증 — PENDING 사용자들의 반복 조회 |
| E2E time_to_completed p99 | 50s 수준에서 수평 수렴 — 완료가 멈춘 상태가 지속됨 |
| JVM Live Threads | 최대 125 수준 — Spring 포화 없음 |
| Hikari Pending Connections | 0 유지 — DB connection pool 여유로움 |

해석:

- submit API와 polling GET 자체는 빠르게 응답했다.
- 그러나 실제 Supabase 조회를 포함한 추천 처리와 Spring callback 저장이 1000 VU 유입 속도를 따라가지 못했다.
- 약 700 VU 이후 완료 수가 374건에서 장시간 정체됐다.
- 테스트 종료 시 1000개 iteration이 완료되지 못하고 interrupted 됐다.
- 따라서 1000 VU에서는 추천 처리/콜백 파이프라인이 적체되고, `PENDING` 상태가 대량 누적된다.

---

## SSE 전환 근거

SSE 전환 근거는 다음 문장으로 정리한다.

```text
1000 VU에서 submit/polling API 자체의 p95는 낮았지만,
전체 제출 1,374건 중 완료는 374건으로 completion coverage가 27.2%에 그쳤다.
테스트 중 PENDING polling 응답은 34,067건 누적됐고, 테스트 종료 뒤에도 PENDING 상태가 대량으로 남았다.
따라서 SSE 전환의 핵심 근거는 polling API 속도 개선이 아니라,
장시간 PENDING 상태에서 반복 조회를 줄이고 추천 진행/완료 이벤트를 push하기 위한 구조 개선이다.
```

SSE가 해결하는 것:

```text
대기 중인 사용자의 반복 polling 요청 감소
장시간 PENDING 상태에서 진행/완료 이벤트 push
프론트가 추천 처리 상태를 더 명확하게 표현할 수 있는 기반 마련
```

SSE가 해결하지 않는 것:

```text
SSE는 FastAPI 추천 처리량, Supabase 조회 성능, Spring callback timeout 자체를 해결하지 않는다.
이 병목은 별도로 callback 동시성, FastAPI worker 수, Supabase 조회 쿼리, 후보 pool 크기, timeout/retry 정책으로 다뤄야 한다.
```

---

## 발견된 문제와 원인 특정을 위한 다음 단계

### 발견된 문제

1000 VU ramping 테스트에서 추천 처리 완료율(`completion_coverage`)이 약 300 req/s 도달 시점(21:45)부터 **28% 수준에서 수평**으로 멈췄다.
제출은 1,374건까지 계속 들어왔지만 완료는 374건에서 정체됐고, 테스트 종료 후에도 PENDING 1,933건이 DB에 남았다.

Spring 레이어(Hikari Pending = 0, JVM Threads 정상)는 문제가 없었으므로, **병목은 FastAPI 추천 처리 파이프라인**에 있다.

그러나 이 테스트만으로는 파이프라인 내 어느 단계가 병목인지 특정할 수 없다. 후보는 다음과 같다:

| 병목 후보 | 근거 |
|---|---|
| FastAPI worker 수 부족 | 동시 요청이 쌓이며 처리 대기 |
| Supabase pgvector 조회 슬로우 | 1건당 조회 비용이 커서 처리량 한계 도달 |
| Spring callback timeout 누적 | `httpx.ConnectTimeout`, `CallbackError` 로그 확인됨 |
| 후보 pool 크기 | 클러스터링/재순위 연산 비용이 VU 증가에 비례해 증가 |

### 원인 특정을 위해 필요한 다음 테스트

- [ ] **FastAPI 단독 부하 테스트** — Spring 없이 FastAPI `/recommend` 엔드포인트만 직접 압박해서 처리량 한계(RPS) 측정. Spring callback 경로를 배제하고 추천 처리 자체의 포화 지점 확인.
- [ ] **FastAPI 내부 구간별 latency 측정** — pgvector 조회 / 클러스터링 / 재순위 각 단계의 소요 시간을 로그 또는 OpenTelemetry로 분리해서 어느 단계가 가장 오래 걸리는지 확인.
- [ ] **callback timeout 비율 측정** — FastAPI 로그에서 `ConnectTimeout` / `CallbackError` 건수를 집계해서 처리는 완료됐으나 callback이 실패한 비율 확인. 추천 완료 후 결과 전달 실패인지, 추천 처리 자체가 밀리는 건지 분리 가능.
- [ ] **worker 수 변경 비교** — FastAPI uvicorn worker 수를 늘린 뒤 동일 조건 재측정. `completion_coverage`가 개선되면 worker 부족이 주원인.
- [ ] **VU 단계별 측정** — 100 / 200 / 300 / 500 VU로 단계적으로 올려 `completion_coverage`가 꺾이는 정확한 임계 VU 확인.

---

## 다음 측정에서 추가로 기록할 항목

| 항목 | 기록 이유 |
|---|---|
| `completion coverage` | 전체 제출 대비 실제 완료 비율을 보여준다. |
| `interrupted iterations` | 테스트 종료 시점까지 완료되지 못한 사용자 흐름 수를 보여준다. |
| `pending_responses` | polling이 장시간 대기 상태에서 만드는 반복 조회량을 보여준다. |
| `polling_count_per_review p95` | 사용자 1명당 상태 조회가 얼마나 반복되는지 보여준다. |
| Spring DB `PENDING/COMPLETED` 수 | 테스트 종료 후 backlog가 실제 저장소에 남았는지 확인한다. |
| FastAPI callback timeout 로그 | 추천 처리 완료 후 Spring callback 저장 경로의 병목 여부를 확인한다. |
| Grafana Tomcat/Hikari 지표 | Spring request thread와 DB connection pool 압력을 확인한다. |
