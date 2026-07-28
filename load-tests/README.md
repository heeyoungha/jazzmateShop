# load-tests

추천 E2E 부하 테스트 디렉토리다.

감상문 제출(`POST /api/user-reviews`)부터 추천 완료 확인(`GET /api/user-reviews/{id}` polling)까지의 end-to-end 흐름을 k6로 측정한다.

---

## 디렉토리 구조

```
load-tests/
├── recommendation-e2e.js          # E2E 메인 시나리오
├── polling-baseline.js            # polling 단독 baseline 시나리오
│
├── docker-compose.mock.yml        # Mock AI 스택 (OpenAI 없이 Spring 구조만 테스트)
├── docker-compose.real.yml        # Real 스택 (실제 FastAPI + OpenAI + Supabase)
├── docker-compose.db-real.yml     # DB Real + OpenAI Mock 스택 (메인 부하 테스트용)
│
├── mock-ai-api/                   # Mock AI API 서버 소스
│   └── main.py                    # FastAPI mock 서버 (embedding/reason 지연 시뮬레이션)
│
├── fixtures/                      # 스택 의존 파일
│   └── polling-fake-db-init.sql   # e2e-db 초기화 SQL
│
├── observability/                 # Prometheus, Grafana 설정
│   ├── prometheus.yml             # Prometheus scrape 설정
│   └── grafana/provisioning/      # Grafana datasource, dashboard 자동 로드 설정
│
├── results/                       # 측정 결과
│   ├── 1vu-smoke.json             # 1 VU smoke 테스트 k6 raw summary
│   ├── 1vu-fastapi-metrics-smoke.json
│   ├── 500vu-fastapi-metrics.json
│   ├── 500vu-resource-stats.tsv
│   └── monitoring/                # Grafana 캡처
│       └── 개인화클러스터링/        # 클러스터링/메타DB 적용 후 측정 캡처
│
└── docs/                          # 문서
    └── monitoring-guide.md                    # 모니터링 설정/실행/해석 가이드
```

---

## 스택 모드

| 파일 | FastAPI | OpenAI | 추천 DB | Prometheus remote write | 용도 |
|---|---|---|---|---|---|
| `docker-compose.mock.yml` | mock 서버 (`mock-ai-api/`) | mock (지연만 시뮬레이션) | 없음 | 없음 | Spring 구조 한계 확인, 비용 없음 |
| `docker-compose.real.yml` | 실제 `backendPython` | 실제 호출 | 실제 Supabase | 없음 | 실제 외부 API 포함 소량 smoke (1~10 VU) |
| `docker-compose.db-real.yml` | 실제 `backendPython` | mock (`MOCK_OPENAI=true`) | 실제 Supabase | 있음 | GPT 비용 없이 실제 Supabase 조회 경로 고동시성 테스트 |

### 스택별 차이 상세

**mock** — `mock-ai-api/main.py`를 별도 서버로 띄운다. OpenAI도 Supabase도 호출하지 않고, 환경변수로 embedding/search/reason 지연 시간을 조절할 수 있다. Spring submit/callback/polling 구조 자체의 한계를 비용 없이 확인할 때 사용한다.

**real** — 실제 `backendPython` FastAPI를 띄우고 OpenAI와 Supabase를 모두 실제로 호출한다. 비용과 rate limit 위험이 있어서 1~10 VU 소량 smoke에만 사용한다.

**db-real** — 실제 FastAPI와 실제 Supabase 조회 경로를 사용하되, OpenAI embedding/reason 호출만 fake client로 대체한다(`MOCK_OPENAI=true`). GPT 비용 없이 실제 추천 DB 조회 경로를 압박할 수 있다. Prometheus remote write가 켜져 있어서 k6 metric이 Grafana 대시보드에 실시간으로 표시된다. 고동시성 부하 테스트의 메인 스택이다.

---

## 빠른 시작

### 1. 스택 실행

```bash
# Mock 스택 (외부 의존 없음, .env 불필요)
docker compose -f load-tests/docker-compose.mock.yml up --build

# DB Real 스택 (실제 Supabase + OpenAI mock, .env 필요)
docker compose -f load-tests/docker-compose.db-real.yml up --build
```

- Grafana: `http://localhost:3000` (admin / admin)
- Prometheus: `http://localhost:9090`

### 2. 1 VU smoke

```bash
BASE_URL=http://localhost:18080 \
REQUEST_TIMEOUT=60s \
POLLING_INTERVAL_SECONDS=3 \
MAX_WAIT_SECONDS=180 \
REVIEW_POOL_SIZE=1000 \
VUS=1 DURATION=15s \
K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9090/api/v1/write \
k6 run --out experimental-prometheus-rw load-tests/recommendation-e2e.js
```

### 3. 1000 VU ramping

```bash
BASE_URL=http://localhost:18080 \
REQUEST_TIMEOUT=60s \
POLLING_INTERVAL_SECONDS=3 \
MAX_WAIT_SECONDS=180 \
REVIEW_POOL_SIZE=1000 \
LOAD_PROFILE=ramping \
RAMP_UP_DURATION=1m RAMP_UP_VUS=500 \
HOLD_DURATION=1m HOLD_VUS=1000 \
RAMP_DOWN_DURATION=30s \
K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9090/api/v1/write \
k6 run --out experimental-prometheus-rw \
--summary-export=load-tests/results/1000vu-ramping.json \
load-tests/recommendation-e2e.js
```

---

## 주요 측정 지표

| 지표 | 의미 |
|---|---|
| `completion_coverage` | 전체 제출 대비 완료 비율. 낮을수록 파이프라인 적체 심각 |
| `pending_responses` | PENDING 상태에서 발생한 반복 조회 누적 수 |
| `time_to_completed p95/p99` | 감상문 제출부터 추천 완료까지 걸린 시간 |
| `submit_api_duration p95` | 제출 API 응답 시간 |
| `polling_get_duration p95` | polling GET 응답 시간 |

---

## 참고 문서

- 모니터링 설정/실행/해석: `docs/monitoring-guide.md`
