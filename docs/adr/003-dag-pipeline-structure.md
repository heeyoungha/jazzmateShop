# ADR-003: DAG Pipeline Structure


## Context

OpenAI Batch API는 요청 제출 후 결과가 준비될 때까지 최대 24시간이 걸릴 수 있다. 
크롤링, GPT 요약, 임베딩 처리를 하나의 DAG에 모두 넣으면 실행 흐름은 단순하지만 긴 대기와 재시도 경계가 불명확해진다.

각 단계의 상태를 독립적으로 추적하고, 실패 시 어느 단계부터 재실행할지 명확히 해야 한다.

## Decision

파이프라인을 3개의 DAG로 분리한다.

```text
[DAG 1] URL 수집 + Playwright 크롤링 + GPT Batch 제출
    -> [DAG 2] GPT 결과 처리 + Embedding Batch 제출
        -> [DAG 3] Embedding 결과 처리 + PostgreSQL 저장
```

DAG 간 연결은 `TriggerDagRunOperator`로 처리한다.

| DAG | schedule | 실행 방식 |
|---|---|---|
| DAG 1 | `None` | 수동 트리거. 추후 cron 전환 가능 |
| DAG 2 | `None` | DAG 1에서 트리거 |
| DAG 3 | `None` | DAG 2에서 트리거 |

OpenAI Batch 결과 대기는 Airflow Sensor를 사용하고, worker 슬롯을 반납하기 위해 `mode='reschedule'`을 사용한다.

```python
@task.sensor(
    mode="reschedule",
    poke_interval=300,
    timeout=86400,
)
def wait_for_batch_result(...):
    ...
```

## Rationale

3-DAG 구조를 선택한 이유는 다음과 같다.

- OpenAI Batch 대기와 후속 처리를 단계별로 분리할 수 있다.
- DAG 단위로 실패와 재실행 경계를 명확히 잡을 수 있다.
- Batch 대기 중 worker 슬롯을 오래 점유하지 않는다.
- 각 DAG의 입력과 출력은 DB 상태 테이블을 통해 추적할 수 있다.

## Consequences

- DAG 간 전달 정보는 작고 명확해야 한다.
- 큰 payload는 XCom으로 넘기지 않고 DB에 저장해야 한다.
- DAG 2, 3는 직접 스케줄링하지 않고 upstream DAG에서 트리거한다.
- DAG별 상태와 Batch 상태는 DB 모델과 일관되어야 한다.

## Related ADRs

- [ADR-002: Airflow CeleryExecutor](002-airflow-celery-executor.md)
- [ADR-004: DB Schema and State Model](004-db-schema-and-state-model.md)
- [ADR-006: TaskFlow API](006-taskflow-api.md)
