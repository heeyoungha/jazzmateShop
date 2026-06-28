# 모니터링 가이드

## 1. 요청 흐름과 병목 후보

추천 E2E 부하 테스트에서 지연 시간이 증가했을 때 **어디에 줄이 생기는지** 빠르게 좁힌다.

핵심은 느린 API 하나만 보는 것이 아니라, 그 API가 기다리는 shared resource를 찾는 것이다.

```text
k6
-> Spring submit (Tomcat thread, Hikari pool)
-> DB insert
-> Spring event listener (@Async executor)
-> FastAPI 추천 처리 (embedding, pgvector 검색, reason 생성)
-> Spring callback 저장
-> DB recommendation 저장
-> k6 polling
```

### 병목 후보

| 병목 위치 | 대표 신호 |
|---|---|
| Spring Tomcat thread | `tomcat_threads_busy_threads` 증가 |
| Hikari DB pool | `hikaricp_connections_pending > 0` |
| Spring async/event | `AiRecommendationClient` 로그가 `http-nio-*` thread에서 찍힘 |
| FastAPI 추천 처리 | `completion coverage` 급락, `pending_responses` 급증 |
| PostgreSQL write | `WALSync`, `WALWrite`, slow query log |

### 판단 순서

```text
1. k6에서 completion_coverage / pending_responses 먼저 본다.
2. submit/polling p95가 같이 올라갔는지 본다.
3. Tomcat busy thread가 올라갔는지 본다.
4. Hikari pending이 생겼는지 본다.
5. Spring 지표가 안정적인데 coverage만 낮으면 FastAPI/Supabase 병목을 의심한다.
6. DB wait가 의심되면 slow query log로 어떤 SQL이 느린지 확인한다.
```

---

## 2. 스택 실행

### 모드별 compose 파일

| 모드 | 파일 | 용도 |
|---|---|---|
| Mock AI | `docker-compose.mock.yml` | Spring 구조 한계 확인, 비용 없음 |
| Real FastAPI | `docker-compose.real.yml` | 실제 OpenAI/Supabase 소량 smoke |
| DB Real + OpenAI Mock | `docker-compose.db-real.yml` | 실제 Supabase 조회 + GPT 비용 없음 (메인) |

### 실행

```bash
# 메인 스택 (DB Real + OpenAI Mock)
docker compose -f load-tests/docker-compose.db-real.yml up --build

# Grafana: http://localhost:3000 (admin / admin)
# Prometheus: http://localhost:9090
```

### k6 실행 (Prometheus remote write 포함)

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
K6_PROMETHEUS_RW_SERVER_URL=http://localhost:9090/api/v1/write \
k6 run --out experimental-prometheus-rw \
--summary-export=load-tests/results/1000vu-ramping.json \
load-tests/recommendation-e2e.js
```

---

## 3. Grafana에서 볼 지표

대시보드: `http://localhost:3000` → **Jazzmate Load Test**

### k6 패널 (심각도 직접 확인)

| 패널 | PromQL | 해석 |
|---|---|---|
| Completion Coverage | `k6_completed_reviews_total / k6_submitted_reviews_total` | 낮을수록 파이프라인 적체 심각 |
| PENDING 누적 | `k6_pending_responses_total` | 반복 조회 누적량 |
| 제출/완료 누적 | `k6_submitted_reviews_total`, `k6_completed_reviews_total` | 격차가 backlog |
| E2E p99 | `k6_time_to_completed_p99` | 완료까지 걸린 시간 |

### Spring 내부 패널 (병목 위치 확인)

| 패널 | 해석 |
|---|---|
| Tomcat 생성/Busy Thread | busy가 current에 가까우면 thread 포화 |
| Hikari Pending Connections | 0이면 DB pool 여유, 증가하면 DB 병목 |
| JVM Live Threads | thread 수 추이 |
| HTTP Request Rate | polling GET이 폭증하면 PENDING 사용자 반복 조회 |

---

## 4. 터미널 보조 확인

### Docker 리소스

```bash
docker stats --no-stream
```

| 항목 | 해석 |
|---|---|
| `ai-api` CPU 100% | FastAPI 처리 포화 |
| `java-backend` CPU 100% | Spring 처리 병목 |
| `e2e-db` BLOCK I/O 증가 | WAL/write 병목 |

### PostgreSQL wait_event

```bash
docker compose -f load-tests/docker-compose.db-real.yml exec -T e2e-db \
psql -U jazzmate -d jazzmate_e2e_loadtest \
-c "select state, wait_event_type, wait_event, count(*)
    from pg_stat_activity
    group by state, wait_event_type, wait_event
    order by count(*) desc;"
```

| 관측값 | 해석 |
|---|---|
| `WALSync`, `WALWrite` | commit/write flush 대기 |
| `Lock` wait 다수 | lock contention |
| 대부분 `idle ClientRead` | DB 자체는 여유로움 |

### Spring 로그 thread 이름

```bash
docker compose -f load-tests/docker-compose.db-real.yml logs --tail=200 java-backend
```

`AiRecommendationClient`가 `http-nio-*`에서 찍히면 @Async가 분리되지 않은 것이다.

---

## 5. 세팅 확인 명령어

```bash
# Spring Actuator
curl http://localhost:18080/actuator/prometheus | grep tomcat_threads
curl http://localhost:18080/actuator/prometheus | grep hikaricp_connections

# Prometheus target 상태
curl -s http://localhost:9090/api/v1/targets | python3 -c \
  "import sys,json; [print(t['labels']['job'], t['health']) for t in json.load(sys.stdin)['data']['activeTargets']]"

# k6 metric 수집 확인 (테스트 후)
curl -s "http://localhost:9090/api/v1/label/__name__/values" | \
  python3 -c "import sys,json; print('\n'.join(n for n in json.load(sys.stdin)['data'] if n.startswith('k6_')))"
```
