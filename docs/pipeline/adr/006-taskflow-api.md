# ADR-006: TaskFlow API


## Context

Airflow DAG는 여러 Python task로 구성된다. DAG 코드에서는 오케스트레이션 흐름이 잘 드러나야 하고, task 간 의존성과 데이터 전달 방식이 과하게 흩어지지 않아야 한다.

단, 크롤링 결과나 임베딩 벡터처럼 큰 데이터는 Airflow XCom에 저장하면 안 된다.

## Decision

DAG 정의에는 `@dag`와 `@task` 데코레이터 기반의 TaskFlow API를 사용한다.

```python
@dag(...)
def my_pipeline():
    @task
    def extract() -> int:
        record_id = run_extract()
        return record_id

    @task
    def transform(record_id: int) -> int:
        processed_id = run_transform(record_id)
        return processed_id

    raw_id = extract()
    transform(raw_id)
```

## Alternatives Considered

### PythonOperator with explicit DAG

```python
t1 = PythonOperator(task_id="extract", python_callable=extract, dag=my_dag)
t2 = PythonOperator(task_id="transform", python_callable=transform, dag=my_dag)
```

Task가 늘어날수록 `dag=` 반복이 많아지고 누락 위험이 있다.

### PythonOperator inside `with DAG(...)`

```python
with DAG(...):
    t1 = PythonOperator(task_id="extract", python_callable=extract)
    t2 = PythonOperator(task_id="transform", python_callable=transform)
    t1 >> t2
```

의존성과 데이터 흐름을 별도로 관리해야 한다.

### TaskFlow API

함수 호출 순서가 의존성 선언이 되고, 작은 값은 return과 인자로 전달할 수 있다.

## Rationale

TaskFlow API를 선택한 이유는 다음과 같다.

- 함수 단위로 task를 정의할 수 있다.
- task 간 의존성이 Python 호출 흐름으로 드러난다.
- 작은 값은 return과 인자로 XCom 전달이 자동화된다.
- Airflow 공식 권장 방식이다.

## XCom Policy

XCom에는 작은 식별자만 전달한다.

허용 예시는 다음과 같다.

- `batch_id`
- `processing_job_id`
- `crawl_job_id`
- 파일 경로
- 작은 status 값

금지 예시는 다음과 같다.

- 크롤링 원문 HTML
- 리뷰 본문 전체
- GPT 결과 JSON 전체
- 임베딩 벡터
- 대량 URL 목록

큰 데이터는 PostgreSQL에 저장하고 ID만 XCom으로 전달한다.

```python
@task
def crawl() -> int:
    results = run_playwright_crawler()
    record_id = supabase.insert(results)
    return record_id
```

## Consequences

- DAG 파일은 오케스트레이션 중심으로 유지한다.
- 비즈니스 로직은 `pipeline_services/` 또는 `dags/crawling/` 모듈에 둔다.
- XCom 크기 제한을 피하기 위해 DB 상태 모델과 함께 설계해야 한다.

## Related ADRs

- [ADR-003: DAG Pipeline Structure](003-dag-pipeline-structure.md)
- [ADR-004: DB Schema and State Model](004-db-schema-and-state-model.md)
- [ADR-005: Failure and Idempotency Strategy](005-failure-idempotency-strategy.md)
