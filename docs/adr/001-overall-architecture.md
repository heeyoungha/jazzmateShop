# ADR-001: Overall Architecture

## Context

AllAboutJazz 재즈 리뷰를 수집한 뒤 GPT 요약, 임베딩 생성, 저장까지 이어지는 배치성 데이터 파이프라인이 필요하다.

파이프라인은 다음 특성을 가진다.

- 외부 웹사이트 크롤링이 포함되어 실패와 지연 가능성이 높다.
- OpenAI Batch API는 결과 대기 시간이 길 수 있다.
- 각 단계의 결과와 실패 이력을 추적해야 한다.
- 재실행 시 중복 데이터와 중복 API 호출을 피해야 한다.
- 추후 처리량 증가에 대비해 worker 확장 경로가 필요하다.

## Decision

Airflow 기반 3단계 배치 파이프라인으로 구성한다.

```text
URL 수집/크롤링
  -> GPT 요약 처리
  -> 임베딩 처리 및 저장
```

핵심 구성은 다음과 같다.

| 영역 | 결정 |
|---|---|
| 오케스트레이션 | Apache Airflow |
| 실행 구조 | CeleryExecutor + Redis broker |
| 크롤링 | Playwright |
| 요약 | OpenAI GPT Batch API |
| 임베딩 | OpenAI Embedding Batch API |
| 상태 저장 | Supabase/PostgreSQL |
| 실패 이력 | PostgreSQL `error_history` |
| 알림 | Slack Webhook |

## Rationale

Airflow는 DAG 단위 실행, task retry, 상태 가시화, 수동/예약 실행을 기본으로 제공한다. 
이 프로젝트는 외부 API 대기와 부분 실패 처리가 중요하므로, 단순 Cron이나 단일 Python script보다 Airflow가 적합하다.

상태와 결과는 Airflow XCom에 크게 의존하지 않고 PostgreSQL에 저장한다. XCom은 task 간 작은 ID 전달에만 사용한다.

## Consequences

- DAG, 서비스 레이어, DB 상태 모델을 명확히 분리해야 한다.
- 긴 대기 작업은 worker 슬롯을 점유하지 않도록 설계해야 한다.
- 모든 단계는 재시도와 재실행을 고려해 멱등적으로 작성해야 한다.
- 구체적인 실행기, DAG 구조, DB 모델, 실패 전략은 후속 ADR을 따른다.

## Related ADRs

- [ADR-002: Airflow CeleryExecutor](002-airflow-celery-executor.md)
- [ADR-003: DAG Pipeline Structure](003-dag-pipeline-structure.md)
- [ADR-004: DB Schema and State Model](004-db-schema-and-state-model.md)
- [ADR-005: Failure and Idempotency Strategy](005-failure-idempotency-strategy.md)
- [ADR-006: TaskFlow API](006-taskflow-api.md)
