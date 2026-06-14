# 1. Request Flow 아키텍처

## 목적

추천 E2E 부하 테스트에서 지연 시간이 증가했을 때 **어디에 줄이 생기는지** 빠르게 좁힌다.

핵심은 느린 API 하나만 보는 것이 아니라, 그 API가 기다리는 shared resource를 찾는 것이다.

```text
느린 API만 보지 말고,
그 API가 기다리는 줄이 어디에 생겼는지 본다.
```

## 요청 흐름

```text
┌─────┐
│ k6  │
└──┬──┘
   │ 1. POST /api/user-reviews
   ▼
┌────────────────────────────────────┐
│ Spring Boot                         │
│ - Tomcat request thread             │
│ - UserReviewService                 │
│ - Transaction commit                │
└──┬─────────────────────────────────┘
   │ 2. INSERT user_reviews
   ▼
┌────────────────────────────────────┐
│ PostgreSQL e2e-db                   │
│ - user_reviews                      │
│ - recommend_album                   │
│ - WAL/write                         │
└──▲─────────────────────────────────┘
   │
   │ 3. commit 후 추천 요청 이벤트
   │
   ▼
┌────────────────────────────────────┐
│ Spring RecommendationEventListener  │
│ - @TransactionalEventListener       │
│ - @Async annotation 존재            │
│ - @EnableAsync 설정은 현재 없음     │
│ - AiRecommendationClient            │
└──┬─────────────────────────────────┘
   │ 4. POST /recommend/review
   ▼
┌────────────────────────────────────┐
│ Mock AI API                         │
│ - embedding delay mock              │
│ - reason delay mock                 │
│ - callback 전송                     │
└──┬─────────────────────────────────┘
   │ 5. POST /api/user-reviews/{id}/recommendations
   ▼
┌────────────────────────────────────┐
│ Spring Boot callback                │
│ - RecommendAlbumService             │
│ - saveAll recommendations           │
│ - review status COMPLETED           │
└──┬─────────────────────────────────┘
   │ 6. INSERT recommend_album
   │    UPDATE user_reviews
   ▼
┌────────────────────────────────────┐
│ PostgreSQL e2e-db                   │
└──▲─────────────────────────────────┘
   │
   │ 7. GET /api/user-reviews/{id} polling
   │
┌──┴──┐
│ k6  │
└─────┘
```

짧게 표현하면 다음과 같다.

```text
k6
-> Spring submit
-> DB insert
-> Spring event listener
-> Mock AI
-> Spring callback
-> DB recommendation 저장
-> k6 polling
```

## 병목 후보

| 병목 위치 | 무슨 일이 생기나 | 대표 신호 |
|---|---|---|
| k6 -> Spring 입구 | 요청이 Tomcat thread를 기다림 | `submit p95`, `polling p95` 동시 증가 |
| Spring Tomcat thread | request thread가 오래 점유됨 | `tomcat_threads_busy_threads` 증가 |
| Spring async/event | 추천 요청이 진짜 비동기로 분리되지 않음 | `AiRecommendationClient` 로그가 `http-nio-*` thread에서 찍힘 |
| Hikari DB pool | DB connection을 기다림 | `hikaricp_connections_pending > 0` |
| PostgreSQL write | insert/update commit이 느림 | `WALSync`, `WALWrite`, slow query log |
| Mock AI API | callback 서버가 CPU-bound | `ai-api` CPU 100% 근처 |

## 현재 500 VU 테스트 해석

```text
기능 실패는 없음
        │
        ▼
submit/polling p95가 초 단위로 증가
        │
        ▼
Spring thread 압박 또는 외부 callback 경로 지연 의심
        │
        ├─ 로그: AiRecommendationClient가 http-nio-*에서 실행됨
        │       -> @Async가 의도대로 분리되지 않았을 가능성
        │
        ├─ docker stats: ai-api CPU 90-105%
        │       -> mock AI callback 서버도 포화 후보
        │
        └─ pg_stat_activity: DB connection 지속 포화는 아님
                -> DB pool 고갈보다는 2차 후보
```

## 항목별 설정과 확인 방법 요약

| 항목 | 설정해야 하는 것 | k6 실행 중 확인 | 병목으로 보는 신호 |
|---|---|---|---|
| k6 E2E 결과 | 별도 설정 없음 | k6 summary | `submit p95`, `polling p95`, `time_to_completed p95` 급증 |
| Spring Tomcat thread | Actuator + Prometheus/Grafana | Grafana `tomcat_threads_*` | busy thread가 current/max에 가까움 |
| Hikari DB pool | Actuator + Prometheus/Grafana | Grafana `hikaricp_connections_*` | `pending > 0`, `idle = 0` |
| JVM thread/CPU | Actuator + Prometheus/Grafana | Grafana `jvm_threads_*`, `process_cpu_usage` | thread 급증, CPU 고정 상승 |
| Mock AI CPU | 별도 설정 없음 | `docker stats --no-stream` | `ai-api` CPU 100% 근처 반복 |
| PostgreSQL wait | 별도 설정 없음 | `pg_stat_activity` | `WALSync`, `WALWrite`, `Lock` wait 다수 |
| PostgreSQL slow query | Postgres slow query log 설정 | `docker compose logs e2e-db` | 100ms~500ms 이상 SQL 반복 |
| Spring async 동작 | 로그 thread 이름 확인 | `docker compose logs java-backend` | `AiRecommendationClient`가 `http-nio-*`에서 실행 |

## 판단 순서

```text
1. k6에서 submit/polling/time_to_completed 중 무엇이 느려졌는지 본다.
2. Tomcat busy thread가 같이 올라갔는지 본다.
3. Hikari pending이 생겼는지 본다.
4. JVM thread가 급증했는지 본다.
5. Spring 지표가 안정적인데 k6 latency만 증가하면 mock AI CPU와 DB wait를 본다.
6. DB wait가 의심되면 slow query log로 어떤 SQL이 느린지 확인한다.
```

## 현재 프로젝트 기준 결론

현재까지의 관측:

```text
1. 낮은/중간 부하에서는 polling 자체가 병목이라는 근거가 약하다.
2. Mock 500 VU에서는 기능 실패 없이 완료됐지만 submit/polling p95가 초 단위로 증가했다.
3. docker stats에서는 mock ai-api가 90-105% CPU에 반복적으로 도달했다.
4. PostgreSQL은 지속적인 connection 고갈보다는 간헐적인 WAL/write wait에 가까웠다.
5. Spring 로그상 AiRecommendationClient가 Tomcat request thread에서 실행됐다.
6. @Async annotation은 있지만 @EnableAsync / 전용 TaskExecutor 설정이 없어 의도대로 분리되지 않았을 가능성이 높다.
```
