# 3. 모니터링 방법

## 1. 실행 순서

먼저 스택을 띄운다.

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml up --build
```

상태 확인:

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml ps
```

기대 상태:

```text
java-backend Up
ai-api Up
e2e-db Up (healthy)
prometheus Up
grafana Up
```

Prometheus target 확인:

```text
http://localhost:9090/targets
```

Grafana 접속:

```text
http://localhost:3000
```

## 2. k6 baseline 실행

먼저 100 VU로 안정 상태 기준선을 만든다.

```bash
BASE_URL=http://localhost:8080 \
REQUEST_TIMEOUT=10s \
POLLING_INTERVAL_SECONDS=1 \
MAX_WAIT_SECONDS=60 \
VUS=100 \
DURATION=5m \
k6 run load-tests/recommendation-e2e.js
```

기록할 k6 지표:

```text
completion_success_rate
http_req_failed
submit_api_duration p95
polling_get_duration p95
time_to_completed p95
submitted_reviews
completed_reviews
```

## 3. 500 VU ramping 실행

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

해석 기준:

```text
100 VU에서는 정상인데 500 VU에서 특정 지표가 먼저 튀는가?
```

## 4. Grafana에서 확인할 지표

Grafana Explore 또는 dashboard에서 아래 PromQL을 본다.

### 4.1 Tomcat thread

먼저 실제 metric이 노출되는지 확인한다.

```bash
curl -s http://localhost:8080/actuator/prometheus | grep tomcat_threads
```

`tomcat_sessions_*`만 나오고 `tomcat_threads_*`가 안 나오면 `SERVER_TOMCAT_MBEANREGISTRY_ENABLED=true` 설정이 반영되지 않았거나 컨테이너가 재빌드/재시작되지 않은 상태일 수 있다.

```promql
tomcat_threads_busy_threads
```

```promql
tomcat_threads_current_threads
```

해석:

| 패턴 | 해석 |
|---|---|
| busy thread가 current thread에 가까움 | Tomcat request thread 포화 |
| current thread가 부하 중 계속 증가 | request thread 수 증가 |
| submit/polling p95 증가와 함께 busy thread 증가 | Spring request 처리 구간 병목 가능성 |

### 4.2 Hikari connection pool

```promql
hikaricp_connections_active
```

```promql
hikaricp_connections_idle
```

```promql
hikaricp_connections_pending
```

해석:

| 패턴 | 해석 |
|---|---|
| pending > 0 | DB connection pool 대기 발생 |
| active가 max 근처 유지 | connection pool 포화 |
| idle이 0 근처 유지 | 여유 DB connection 없음 |
| pending은 0인데 latency 증가 | DB pool보다 Tomcat/CPU/외부 호출 쪽 의심 |

### 4.3 JVM thread

```promql
jvm_threads_live_threads
```

```promql
jvm_threads_daemon_threads
```

해석:

| 패턴 | 해석 |
|---|---|
| live threads가 부하 중 급증 | Tomcat 또는 executor thread 증가 |
| 부하 종료 후 thread가 감소하지 않음 | thread leak 또는 executor 설정 문제 가능성 |

### 4.4 CPU

```promql
process_cpu_usage
```

```promql
system_cpu_usage
```

해석:

| 패턴 | 해석 |
|---|---|
| process CPU가 높음 | Java 애플리케이션 CPU 병목 가능성 |
| system CPU가 높고 process CPU는 낮음 | Docker Desktop/호스트 자원 병목 가능성 |

### 4.5 HTTP 요청 지연

Spring Boot 3 / Micrometer에서 metric 이름은 환경에 따라 다를 수 있다. 먼저 Grafana Explore에서 `http_server`로 검색한다.

자주 쓰는 형태:

```promql
http_server_requests_seconds_count
```

```promql
http_server_requests_seconds_sum
```

endpoint별 평균 latency 예시:

```promql
rate(http_server_requests_seconds_sum[1m])
/
rate(http_server_requests_seconds_count[1m])
```

가능하면 `uri` label로 나눠서 본다.

```text
/api/user-reviews
/api/user-reviews/{id}
/api/user-reviews/{reviewId}/recommendations
```

해석:

| 패턴 | 해석 |
|---|---|
| POST submit만 느림 | 감상문 저장/추천 요청 발행 구간 의심 |
| callback만 느림 | 추천 결과 저장/write 구간 의심 |
| polling도 같이 느림 | Tomcat thread, DB pool, DB shared resource 병목 가능성 |

## 5. 터미널에서 보조 확인

### 5.1 Docker 리소스

```bash
docker stats --no-stream
```

확인할 것:

| 항목 | 해석 |
|---|---|
| `ai-api` CPU 100% 근처 | mock AI callback 서버가 먼저 포화 |
| `java-backend` CPU 100% 근처 | Spring/Tomcat/JPA/JSON 처리 병목 의심 |
| `e2e-db` CPU 높음 | PostgreSQL 처리 부하 의심 |
| `e2e-db` BLOCK I/O 증가 | write flush/WAL 병목 가능성 |
| memory 지속 증가 | queue 적체 또는 memory leak 의심 |

### 5.2 PostgreSQL wait_event

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

해석:

| 관측값 | 해석 |
|---|---|
| 대부분 `idle ClientRead` | DB가 계속 바쁜 상태는 아닐 가능성 |
| `WALSync`, `WALWrite` | commit/write flush 대기 |
| `BufferContent` | buffer 경합 |
| `Lock` wait 다수 | lock contention 의심 |
| active connection이 계속 많음 | DB 처리량 또는 connection pool 병목 의심 |

### 5.3 PostgreSQL slow query log

slow query log를 켠 경우:

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml logs -f e2e-db
```

볼 것:

```text
duration: ... ms  statement: ...
```

해석:

| 느린 SQL | 의심 구간 |
|---|---|
| `insert into user_reviews` | submit 저장 |
| `insert into recommend_album` | callback 추천 결과 저장 |
| `update user_reviews` | status COMPLETED 전이 |
| `select ... user_reviews` | polling 조회 |

### 5.4 Spring 로그 thread 이름

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml logs --tail=200 java-backend
```

문제 의심 패턴:

```text
http-nio-8080-exec-344
http-nio-8080-exec-498
http-nio-8080-exec-525
```

이 형태는 추천 요청 전송이 별도 async executor가 아니라 Tomcat request thread에서 실행되고 있다는 뜻이다.

개선 후 기대 패턴:

```text
recommendation-executor-1
recommendation-executor-2
```

실제 이름은 `ThreadPoolTaskExecutor` 설정의 `threadNamePrefix`에 따라 달라진다.

### 5.5 Java thread 수

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml exec -T java-backend \
sh -c 'ps -T | wc -l'
```

thread 목록 일부:

```bash
docker compose -f load-tests/docker-compose.recommendation-e2e.yml exec -T java-backend \
sh -c 'ps -T | sed -n "1,100p"'
```

## 6. 최종 판정 예시

| 관측 | 병목 후보 |
|---|---|
| k6 submit p95 증가 + Tomcat busy 증가 | Spring request thread 압박 |
| k6 submit/polling p95 증가 + Hikari pending 증가 | DB connection pool 대기 |
| Hikari pending 없음 + ai-api CPU 100% | mock AI callback 서버 포화 |
| DB wait에 `WALSync/WALWrite` 반복 + slow query log에 INSERT/UPDATE 지연 | PostgreSQL write/WAL 병목 |
| `AiRecommendationClient` 로그가 `http-nio-*` | 추천 요청 전송이 Tomcat request thread에서 실행됨 |

## 7. 다음 개선 확인

개선 작업 후에는 같은 500 VU ramping을 다시 실행한다.

비교할 값:

```text
submit_api_duration p95
polling_get_duration p95
time_to_completed p95
tomcat_threads_busy_threads
hikaricp_connections_pending
jvm_threads_live_threads
```

특히 `@EnableAsync`와 전용 executor를 추가한 뒤에는 `AiRecommendationClient` 로그 thread 이름이 `http-nio-*`에서 전용 executor prefix로 바뀌는지 확인한다.
