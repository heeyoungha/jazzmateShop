# ADR-002: Airflow CeleryExecutor

## Context

파이프라인은 크롤링, OpenAI Batch 제출, Batch 결과 대기, DB 저장 등 여러 task로 구성된다. 
일부 task는 짧게 끝나지만, OpenAI Batch 결과 대기는 길게 지속될 수 있다.

초기에는 단일 머신 또는 Docker Compose 기반으로 시작하되, 추후 worker를 늘릴 수 있는 구조가 필요하다.

## Decision

Airflow 실행기는 `CeleryExecutor`를 사용하고, Redis를 Celery broker로 둔다.

```text
Scheduler -> Redis queue -> Celery Worker
          <- Result Backend(DB)
```

## Alternatives Considered

| 방식 | 장점 | 단점 |
|---|---|---|
| Cron + Python script | 구현 단순 | 재시도, 대기, 상태 가시화 직접 구현 필요 |
| Airflow + LocalExecutor | Airflow 기능 사용 가능 | 단일 서버 고정, 수평 확장 제한 |
| Airflow + CeleryExecutor | 가시성, retry, worker 확장 가능 | Redis 추가로 인프라 복잡도 증가 |

## Rationale

CeleryExecutor를 선택한 이유는 다음과 같다.

- Airflow UI에서 DAG 흐름, task 상태, 로그를 확인할 수 있다.
- task별 retry 정책과 실패 처리를 Airflow에 위임할 수 있다.
- worker를 추가해 처리량을 늘릴 수 있다.
- Sensor를 `reschedule` 모드로 사용하면 긴 대기 중 worker 슬롯을 반납할 수 있다.

## Consequences

- Redis가 추가 장애 포인트가 된다.
- 장애 분석 시 Airflow Scheduler, Webserver, Worker, Redis 로그를 함께 봐야 한다.
- Docker Compose 구성에는 Airflow 구성요소와 Redis, worker 서비스가 포함된다.
- DAG 코드는 LocalExecutor나 KubernetesExecutor로 전환해도 가능한 한 재사용 가능해야 한다.

## Future Migration

처리량이 늘거나 동적 리소스 할당이 필요해지면 KubernetesExecutor로 전환할 수 있다.

전환 조건 예시는 다음과 같다.

- DAG 수가 크게 증가한다.
- 실행 빈도가 일 단위 이상으로 높아진다.
- 크롤링, 요약, 임베딩 task별 리소스 요구량이 크게 달라진다.

## Related ADRs

- [ADR-001: Overall Architecture](001-overall-architecture.md)
- [ADR-003: DAG Pipeline Structure](003-dag-pipeline-structure.md)
