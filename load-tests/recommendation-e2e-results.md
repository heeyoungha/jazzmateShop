# 추천 E2E k6 결과

## 측정 맥락

- 대상 흐름: `POST /api/user-reviews` -> `GET /api/user-reviews/{id}` polling -> terminal status 확인
- 종료 상태: `COMPLETED`, `FAILED`, `MAX_WAIT_SECONDS` 초과 timeout
- 목적: polling API 단독 성능이 아니라, 감상문 제출부터 추천 완료 확인까지의 end-to-end 지연 시간을 측정한다.

## 실행 명령

### Mock E2E 스택 시작

기본 compose는 load-test 전용 mock AI API를 사용한다. 따라서 OpenAI 키와 Supabase 키가 필요 없다.

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml up --build
```

Mock 지연 시간은 환경변수로 조절할 수 있다.

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

### Mock 구조 부하 테스트

```bash
BASE_URL=http://localhost:8080 \
REQUEST_TIMEOUT=10s \
POLLING_INTERVAL_SECONDS=1 \
MAX_WAIT_SECONDS=60 \
VUS=100 \
DURATION=5m \
k6 run load-tests/recommendation-e2e.js
```

### Mock 500 VU 이상 ramping 테스트

500 VU 이상에서는 `constant-vus`로 즉시 시작하면 초기 연결 spike가 결과를 지배할 수 있다. sustained throughput을 보려면 ramping profile을 사용한다.

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

## 결과 표

| 모드 | VU | 총 리뷰 | 완료 | 실패 | Timeout | submit p95 | time_to_completed p95 | time_to_completed p99 | 평균 polling 횟수 | 비고 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Real OpenAI | 1 | 7 | 7 | 0 | 0 | 412.6 ms | 14.65 s | N/A | 3.29 | `completion_success_rate=100%`, `http_req_failed=0%` |
| Real OpenAI | 5 | 235 | 235 | 0 | 0 | 21.95 ms | 6.03 s | N/A | 1.28 | `completion_success_rate=100%`, `http_req_failed=0%` |
| Real OpenAI | 10 | 513 | 513 | 0 | 0 | 45.98 ms | 6.02 s | N/A | 1.17 | threshold 전체 통과, `http_req_failed=0%` |
| Mock OpenAI | 100 | 14,606 | 14,606 | 0 | 0 | 92.27 ms | 2.11 s | N/A | 2.00 | `48.45 reviews/s`, threshold 전체 통과 |
| Mock OpenAI | 500 ramping | 25,888 | 25,888 | 0 | 0 | 2.05 s | 7.15 s | N/A | 2.26 | `66.19 reviews/s`, 성공률 100%, latency threshold 초과 |
| Mock OpenAI | 1000 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

참고: 500 `constant-vus` 초기 실행에서는 `POST /api/user-reviews`에서 `connection reset by peer`가 발생했다. 이 결과는 sustained throughput 한계라기보다 0초에 500 VU가 동시에 연결을 만드는 startup spike로 분리해서 봐야 한다.

## 결과 해석

Real OpenAI E2E smoke/small-load는 10 VU까지 성공했다.

- 1, 5, 10 VU 모두 `completion_success_rate=100%`였다.
- recommendation failure, E2E timeout, submit failure, polling failure, HTTP failure는 없었다.
- polling GET은 낮은 부하에서 가벼웠다. 모든 Real OpenAI run에서 polling GET p95는 54 ms 이하였고, 5/10 VU에서는 10 ms 이하로 유지됐다.
- 5/10 VU의 `time_to_completed p95`는 약 6초였다. 1 VU run의 14.65초는 작은 표본 수, cold start, 외부 API 변동 영향으로 보는 것이 타당하다.
- Mock AI 100 VU에서는 5분 동안 14,606건이 모두 완료됐고, `time_to_completed p95=2.11s`였다.
- Mock AI 500 VU ramping에서는 25,888건이 모두 완료됐지만 `submit_api_duration p95=2.05s`, `polling_get_duration p95=1.82s`로 지연 시간이 급증했다. 이 지점이 현재 로컬 구조 테스트에서 처음 확인된 saturation signal이다.

100 VU와 500 VU를 비교하면 병목 신호가 더 명확하다.

| 지표 | 100 VU | 500 VU ramping | 변화 |
|---|---:|---:|---:|
| 처리량 | 48.45 reviews/s | 66.19 reviews/s | 약 1.37배 증가 |
| submit p95 | 92.27 ms | 2.05 s | 약 22배 증가 |
| polling GET p95 | 50.23 ms | 1.82 s | 약 36배 증가 |
| time_to_completed p95 | 2.11 s | 7.15 s | 약 3.4배 증가 |
| 실패율 | 0% | 0% | 동일 |

즉, 500 VU에서 기능 실패는 없었지만 처리량 증가폭보다 지연 시간 증가폭이 훨씬 컸다. 요청이 더 많이 들어오자 내부 대기열 또는 shared resource에서 줄이 생기기 시작한 것으로 해석한다.

## 500 VU 병목 확인

500 VU ramping 실행 중 `docker stats`와 PostgreSQL `pg_stat_activity`를 약 10초 간격으로 샘플링했다.

관측된 신호:

- `ai-api` CPU가 반복적으로 90-105%에 도달했다. Java와 PostgreSQL은 보통 그보다 낮았다.
- `java-backend` CPU는 대략 20-75% 범위로 변동했고, Java process/thread 수는 일시적으로 약 250 PIDs까지 증가했다.
- `e2e-db` CPU도 변동했지만 대체로 Java/AI보다 낮았고, WAL 활동 시점에만 짧게 spike가 있었다.
- PostgreSQL connection은 지속적으로 포화되지 않았다. 대부분 샘플에서 Spring connection 약 10개가 `idle ClientRead` 상태였다.
- write burst 시점에만 `WALSync`, `WALWrite`, `BufferContent`, `idle in transaction` 같은 DB wait가 짧게 보였다.

현재 병목 가설:

- 1차 후보: mock `ai-api` 단일 프로세스 callback 경로가 500 VU 부근에서 CPU-bound가 된다.
- 2차 후보: callback write가 몰리는 순간 PostgreSQL WAL/write wait가 간헐적으로 발생한다.
- 현재 샘플로는 아직 근거가 약한 후보: 지속적인 PostgreSQL connection 고갈, 지속적인 DB lock contention.

## Spring 내부 확인

Spring 쪽에서도 병목 후보가 확인됐다.

- Actuator dependency는 이미 있지만, 기존 실행 컨테이너는 `/actuator/health`만 노출하고 있었다.
- 다음 측정을 위해 E2E compose에 `MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE=health,metrics`를 추가했다.
- 기준선 측정 당시 Java backend에서 `@EnableAsync` 또는 전용 `TaskExecutor` 설정을 찾지 못했다.
- load-test 로그에서 `AiRecommendationClient`가 별도 async executor thread가 아니라 `http-nio-8080-exec-*` Tomcat request thread에서 실행되는 것이 확인됐다.
- 500 VU 부하 중 Tomcat request thread 이름은 `http-nio-8080-exec-525`처럼 높은 suffix까지 증가했고, Java process/thread 수는 약 250 PIDs까지 증가했다.

현재 Spring 가설:

- 현재 runtime에서는 `@Async`가 효과적으로 활성화되어 있지 않다.
- `POST /api/user-reviews` 요청 thread가 transaction commit 이후 FastAPI 추천 요청 전송까지 맡고 있을 가능성이 높다.
- 고부하에서는 이 때문에 Tomcat request thread 점유 시간이 늘고, submit 응답과 polling GET 응답이 함께 느려질 수 있다.

## Grafana 100 VU vs 500 VU 비교

Grafana 캡처:

```text
100 VU: load-tests/monitoring/100/
500 VU: load-tests/monitoring/500/
500 VU + EnableAsync: load-tests/monitoring/500_EnableAsync/
```

관측 비교:

| 지표 | 100 VU | 500 VU ramping | 해석 |
|---|---:|---:|---|
| `tomcat_threads_current_threads` | 약 100 | 200 도달 | Tomcat thread pool이 최대치까지 확장됨 |
| `tomcat_threads_busy_threads` | 순간 30대 | 200 근처 spike | 요청 처리 thread가 포화 구간에 도달 |
| `hikaricp_connections_active` | 순간 10 근처 | 10 근처 반복 | Hikari 기본 max pool 근처까지 사용 |
| `hikaricp_connections_pending` | 순간 spike, 최대 약 17 | 최대 약 180~190 | DB connection pool 대기가 강하게 발생 |
| `jvm_threads_live_threads` | 약 140대 | 약 230대 | Tomcat/request 처리 thread 증가 |
| `process_cpu_usage` | 초기 spike 후 낮음 | 높게 유지되진 않음 | Java CPU 자체보다 thread/connection 대기 영향이 더 큼 |

이 비교로 보면 500 VU에서는 단순히 mock AI만 병목이라고 보기 어렵다. Grafana 기준으로는 `Tomcat thread pool max 도달`과 `Hikari pending connection 급증`이 동시에 보였으므로, Spring request thread와 DB connection pool 대기가 주요 병목 후보로 올라간다.

특히 `hikaricp_connections_pending`이 100 VU에서는 순간 spike였지만, 500 VU에서는 180 이상까지 크게 증가했다. 이는 많은 요청이 DB connection을 얻기 위해 기다렸다는 뜻이다. 따라서 500 VU의 `submit p95=2.05s`, `polling p95=1.82s` 증가는 Hikari pool 대기와 Tomcat thread 포화가 함께 만든 지연으로 해석하는 것이 타당하다.

## Grafana 500 VU 기준선 vs EnableAsync 적용 후 비교

`@EnableAsync`와 전용 `ThreadPoolTaskExecutor` 적용 후 500 VU를 다시 관측했다.

Grafana 캡처:

```text
500 VU + EnableAsync: load-tests/monitoring/500_EnableAsync/
```

관측 비교:

| 지표 | 500 VU 기준선 | 500 VU + EnableAsync | 해석 |
|---|---:|---:|---|
| `tomcat_threads_current_threads` | 200 도달 | 200 도달 | 생성된 Tomcat thread 수는 여전히 max까지 증가 |
| `tomcat_threads_busy_threads` | 200 근처 spike | 최대 약 45 spike | 실제 요청 처리 중인 Tomcat thread 포화는 크게 완화 |
| `hikaricp_connections_active` | 10 근처 반복 | 순간 10 도달 | DB connection 사용량 spike는 남아 있으나 지속 포화는 약화 |
| `hikaricp_connections_idle` | 낮은 구간 반복 | 대부분 10, 순간적으로만 감소 | 여유 connection이 대부분 유지됨 |
| `hikaricp_connections_pending` | 최대 약 180~190 | 최대 약 7 | DB connection pool 대기가 크게 감소 |
| `jvm_threads_live_threads` | 약 230대 | 약 250대 | 전용 executor 추가로 JVM thread 수는 증가 가능 |
| `process_cpu_usage` | 높게 유지되진 않음 | 약 0.1~0.15 수준 유지 | Java CPU 병목으로 보기는 어려움 |

해석:

```text
EnableAsync 적용 후 Tomcat busy thread와 Hikari pending이 동시에 크게 감소했다.
이는 추천 요청 전송이 Tomcat request thread에서 분리되면서
request thread 점유 시간이 줄었고, DB connection 대기 압력도 함께 낮아졌다는 뜻이다.

다만 tomcat_threads_current_threads는 여전히 200까지 증가했다.
current thread는 생성된 thread 수까지 포함하므로, busy thread가 낮다면
그 자체만으로 request thread 포화라고 보지는 않는다.

다음 비교에는 k6 요약의 submit_api_duration p95, polling_get_duration p95,
time_to_completed p95를 함께 기록해야 실제 사용자 지연 개선 폭을 확정할 수 있다.
```

## 병목 후보 우선순위

500 VU ramping 결과와 Grafana 지표를 함께 보면 병목 후보 우선순위는 다음과 같다.

### 1. Hikari DB connection pool 대기

근거:

```text
100 VU: hikaricp_connections_pending이 순간 spike 수준
500 VU: hikaricp_connections_pending이 약 180~190까지 급증
```

해석:

```text
많은 요청이 DB connection을 얻지 못하고 대기했다.
submit, callback, polling이 모두 DB connection pool을 공유하므로
submit p95와 polling p95가 함께 증가할 수 있다.
```

### 2. Tomcat request thread 포화

근거:

```text
100 VU: tomcat_threads_current_threads 약 100
500 VU: tomcat_threads_current_threads가 max 200에 도달
500 VU: tomcat_threads_busy_threads가 200 근처까지 spike
```

해석:

```text
Tomcat request thread pool이 고부하에서 최대치까지 확장됐다.
요청 처리 thread가 부족해지면 submit과 polling 모두 대기 시간이 증가한다.
```

### 3. @Async 미동작으로 request thread 점유 시간 증가

근거:

```text
RecommendationEventListener에는 @Async annotation이 있었다.
하지만 기준선 측정 당시 @EnableAsync / 전용 TaskExecutor 설정은 없었다.
부하 테스트 로그에서 AiRecommendationClient가 http-nio-8080-exec-* thread에서 실행됐다.
```

해석:

```text
추천 요청 전송이 별도 executor가 아니라 Tomcat request thread에서 실행될 가능성이 높다.
이 경우 POST /api/user-reviews 요청 thread가 FastAPI 요청 전송까지 맡으면서
request thread 점유 시간이 길어진다.
```

### 4. Mock AI CPU 포화

근거:

```text
docker stats에서 ai-api CPU가 90~105%에 반복적으로 도달했다.
```

해석:

```text
Mock AI callback 서버도 고부하에서 CPU-bound가 될 수 있다.
다만 Grafana에서 Hikari pending과 Tomcat thread 포화가 명확히 보였으므로
현재 우선순위는 Spring/DB connection pool 쪽이 더 높다.
```

### 5. PostgreSQL WAL/write wait

근거:

```text
pg_stat_activity에서 WALSync, WALWrite, BufferContent wait가 간헐적으로 보였다.
```

해석:

```text
callback 저장 write burst 시점에 PostgreSQL WAL/write wait가 발생할 수 있다.
다만 지속적인 DB lock contention이나 connection 전체 포화 근거는 아직 약하다.
```

## 단계별 해결 이력

이 섹션에는 병목 후보를 하나씩 제거하거나 완화하면서 결과를 누적한다.

| Step | 대상 | 조치 | 기대 효과 | 검증 방법 | 결과 |
|---:|---|---|---|---|---|
| 0 | 기준선 | 100 VU, 500 VU ramping 측정 | 현재 병목 후보 도출 | k6 + Grafana | 500 VU에서 Hikari pending 급증, Tomcat thread max 도달 |
| 1 | @Async / Tomcat thread | `@EnableAsync` + 전용 `ThreadPoolTaskExecutor` 추가 | 추천 요청 전송을 Tomcat request thread에서 분리 | 로그 thread 이름, Tomcat busy, submit p95 | Grafana 기준 개선 확인. k6 요약 수치 추가 필요 |
| 2 | Hikari pool | `maximumPoolSize` 조정 검토 | DB connection 대기 완화 | `hikaricp_connections_pending`, DB CPU/wait, p95 비교 | TODO |
| 3 | DB write | callback 저장 쿼리/트랜잭션 확인, slow query log 분석 | write 지연 원인 분리 | slow query log, `WALSync/WALWrite`, callback latency | TODO |
| 4 | Mock AI | mock AI worker/process 확장 또는 지연 모델 조정 | mock 서버 CPU 병목 제거 | `docker stats`, time_to_completed p95 | TODO |

### Step 0. 기준선 측정 완료

수행한 작업:

```text
1. Real OpenAI 1/5/10 VU E2E 측정
2. Mock AI 100 VU 구조 부하 측정
3. Mock AI 500 VU ramping 구조 부하 측정
4. Grafana로 100 VU와 500 VU의 Tomcat/Hikari/JVM 지표 비교
```

결론:

```text
100 VU는 안정적이었다.
500 VU에서는 기능 실패는 없었지만 submit/polling latency가 초 단위로 증가했다.
Grafana상 Hikari pending connection이 급증했고 Tomcat thread가 max에 도달했다.
따라서 다음 해결 우선순위는 @Async 분리와 Hikari/Tomcat 지표 개선이다.
```

### Step 1. @Async 활성화 및 전용 executor 추가

적용한 작업:

```text
1. AsyncConfig 추가
2. @EnableAsync 활성화
3. recommendationTaskExecutor Bean 추가
4. RecommendationEventListener의 @Async에 executor 이름 명시
5. threadNamePrefix를 recommendation-executor-로 지정
```

변경 의도:

```text
기준선에서는 AiRecommendationClient가 http-nio-8080-exec-* Tomcat request thread에서 실행됐다.
전용 executor 적용 후에는 recommendation-executor-* thread에서 실행되어야 한다.
이를 통해 POST /api/user-reviews 요청 thread가 FastAPI 추천 요청 전송까지 점유되는 문제를 완화한다.
```

검증 방법:

```text
1. docker compose up --build로 Java 이미지를 재빌드한다.
2. 500 VU ramping 테스트를 다시 실행한다.
3. java-backend 로그에서 AiRecommendationClient thread 이름이 recommendation-executor-*인지 확인한다.
4. Grafana에서 tomcat_threads_busy_threads, hikaricp_connections_pending, submit p95, polling p95를 기준선과 비교한다.
```

현재 상태:

```text
compileJava 통과.
전체 테스트는 기존 RecommendAlbumBatchRequest 누락으로 compileTestJava에서 실패하므로 별도 수정 필요.
500 VU + EnableAsync Grafana 관측에서 Tomcat busy thread와 Hikari pending이 크게 감소했다.
k6 summary 기준 latency 수치는 아직 문서에 추가되지 않았다.
```

## 혼자 재현하고 확인하는 절차

### 1. Mock E2E 스택을 시작한다

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml up --build
```

다른 터미널에서 컨테이너 상태를 확인한다.

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml ps
```

기대 상태:

```text
java-backend Up
ai-api Up
e2e-db Up (healthy)
```

### 2. Actuator metrics 노출을 확인한다

compose를 재시작한 뒤 아래 명령을 실행한다.

```bash
curl http://localhost:8080/actuator
curl http://localhost:8080/actuator/health
curl http://localhost:8080/actuator/metrics
```

`/actuator` 응답에 `metrics` 링크가 보여야 한다.

주요 지표:

```bash
curl http://localhost:8080/actuator/metrics/tomcat.threads.busy
curl http://localhost:8080/actuator/metrics/tomcat.threads.current
curl http://localhost:8080/actuator/metrics/hikaricp.connections.active
curl http://localhost:8080/actuator/metrics/hikaricp.connections.idle
curl http://localhost:8080/actuator/metrics/hikaricp.connections.pending
```

해석 기준:

- `tomcat.threads.busy`가 계속 높음: Tomcat request thread 포화 의심
- `hikaricp.connections.pending > 0`: DB connection pool 대기 발생
- `hikaricp.connections.active`가 max 근처에서 유지: DB connection pool 사용량 포화
- `hikaricp.connections.idle`이 거의 0: 여유 DB connection 없음

### 3. 500 VU ramping 테스트를 실행한다

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

결과에서 우선 볼 지표:

```text
completion_success_rate
submit_api_duration p95
polling_get_duration p95
time_to_completed p95
http_req_failed
```

500 VU에서 `completion_success_rate=100%`라도 `submit p95`와 `polling p95`가 초 단위로 튀면 saturation signal로 본다.

### 4. 테스트 중 Docker 리소스를 본다

테스트 실행 중 다른 터미널에서 반복 확인한다.

```bash
docker stats --no-stream
```

해석 기준:

- `ai-api` CPU가 100% 근처: mock AI callback 서버가 먼저 포화
- `java-backend` CPU가 100% 근처: Spring/Tomcat/JPA/JSON 처리 병목 의심
- `e2e-db` CPU 또는 block I/O가 높음: PostgreSQL write/read 병목 의심
- memory가 계속 증가: memory leak 또는 queue 적체 의심

### 5. 테스트 중 PostgreSQL wait를 본다

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml exec -T e2e-db \
psql -U jazzmate -d jazzmate_e2e_loadtest \
-c "select state, wait_event_type, wait_event, count(*)
    from pg_stat_activity
    group by state, wait_event_type, wait_event
    order by count(*) desc;"
```

connection 수도 확인한다.

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml exec -T e2e-db \
psql -U jazzmate -d jazzmate_e2e_loadtest \
-c "select count(*) as connections from pg_stat_activity;"
```

해석 기준:

- 대부분 `idle ClientRead`: DB가 계속 바쁜 상태는 아닐 가능성
- `WALSync`, `WALWrite`: commit/write flush 대기
- `BufferContent`: buffer 경합
- `Lock` wait 다수: lock contention 의심
- active connection이 계속 많음: DB 쿼리 처리량 또는 connection pool 병목 의심

### 6. Spring 로그에서 thread 이름을 확인한다

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml logs --tail=200 java-backend
```

`AiRecommendationClient` 로그의 thread 이름을 본다.

현재 관측된 형태:

```text
http-nio-8080-exec-344
http-nio-8080-exec-498
http-nio-8080-exec-525
```

이 형태라면 추천 요청 전송이 별도 async executor가 아니라 Tomcat request thread에서 실행되고 있다는 뜻이다.

`@Async`가 제대로 분리되면 로그 thread 이름이 보통 다음처럼 별도 executor 이름으로 바뀌어야 한다.

```text
recommendation-executor-1
recommendation-executor-2
```

이 이름은 실제 executor 설정에 따라 달라진다.

### 7. Java thread 수를 확인한다

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml exec -T java-backend \
sh -c 'ps -T | wc -l'
```

thread 목록 일부도 볼 수 있다.

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml exec -T java-backend \
sh -c 'ps -T | sed -n "1,100p"'
```

해석 기준:

- 부하 중 thread 수가 계속 증가: Tomcat thread 또는 async executor thread 증가 의심
- `http-nio-8080-e` thread가 많음: Tomcat request thread 사용량 증가
- 별도 executor thread가 안 보임: `@Async` 설정 미작동 가능성

## 다음 결정

현재 증거로는 낮은/중간 부하에서 polling 자체가 병목이라고 보기는 어렵다. Mock 500 VU 구조 테스트에서는 전체 요청이 성공했지만 submit과 polling latency가 threshold를 넘었다.

다음 개선 우선순위:

1. `@EnableAsync`와 전용 `ThreadPoolTaskExecutor` 추가 완료.
2. Java 이미지를 재빌드한 뒤 추천 요청 전송이 Tomcat request thread가 아니라 전용 executor thread에서 실행되는지 로그로 확인한다.
3. Actuator/Grafana metrics로 `tomcat_threads_*`, `hikaricp_connections_*`, JVM thread 지표를 측정한다.
4. 같은 500 VU ramping 테스트를 다시 실행해서 `submit p95`, `polling p95`, `time_to_completed p95`를 기준선과 비교한다.
5. 개선 효과가 확인되면 Hikari pool 조정 또는 1,000 VU 테스트를 검토한다.
