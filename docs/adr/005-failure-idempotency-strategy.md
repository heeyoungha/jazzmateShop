# ADR-005: Failure and Idempotency Strategy


## Context

크롤링과 외부 API 호출은 실패 가능성이 높다. 전체 배치에서 일부 URL만 실패했는데 전체 파이프라인을 중단하면 운영 효율이 낮다.

반대로 네트워크 장애, API rate limit, DB 일시 장애처럼 재시도하면 성공할 수 있는 실패는 Airflow retry와 충돌하지 않게 처리해야 한다.

또한 Airflow task가 재시도되거나 수동으로 재실행되어도 중복 API 호출과 중복 데이터 저장을 피해야 한다.

## Decision

실패를 `RetryableError`와 `PermanentError`로 분류하고, item 단위 부분 실패를 허용한다.

정의 위치는 `pipeline_services/exceptions.py`로 둔다.

## Error Classification

### RetryableError

Airflow retry에 맡길 수 있는 일시적 실패다. 상위로 전파한다.

| 예외 | 발생 상황 |
|---|---|
| `NetworkError` | 네트워크 연결 실패 |
| `TimeoutError` | 요청 시간 초과 |
| `RateLimitError` | API rate limit 도달 |
| `DatabaseError` | DB 작업 실패 |

### PermanentError

재시도해도 같은 item에서 성공 가능성이 낮은 실패다. item 단위로 기록 후 다음 항목 처리를 계속할 수 있다.

| 예외 | 발생 상황 |
|---|---|
| `ValidationError` | 데이터 유효성 검사 실패 |
| `ParseError` | HTML/콘텐츠 파싱 실패 |
| `BlockedError` | 안티봇 감지, IP 차단 |
| `BillingLimitError` | OpenAI 결제 한도 도달 |
| `BatchFailedError` | OpenAI Batch 전체 실패/만료/취소 |

## Partial Success

크롤링과 GPT 결과 처리 단계는 성공률이 80% 이상이면 다음 단계로 진행한다.

```python
SUCCESS_RATE_THRESHOLD = 0.8
```

개별 실패는 `error_history`에 기록한다.

성공률이 80% 미만이거나 batch 전체를 진행할 수 없는 영구 오류는 task 또는 DAG를 실패 처리한다.

## crawl_jobs 상태 머신

`crawl_jobs` 테이블이 크롤링 상태 머신 역할을 한다.

```
pending → running → success
                 ↘ failed
```

- Task 시작 시: `pending` → `running`
- Task 성공 시: `running` → `success`
- Task 실패 시: `running` → `failed` (에러는 `error_history`에 기록)
- 재시도 시: `failed` 상태인 job만 재처리 대상으로 선택

## Idempotency

Task가 재시도되거나 중복 실행되어도 데이터 일관성이 유지되도록 한다.

| 대상 | 전략 | 구현 |
|---|---|---|
| URL 등록 | UNIQUE constraint | `crawl_targets.url` 중복 시 무시 |
| 크롤링 저장 | upsert 또는 conflict ignore | `allthatjazz_raw` 중복 저장 방지 |
| OpenAI Batch 제출 | Batch ID 선기록 | 재시도 시 중복 API 호출 방지 |
| 임베딩 저장 | upsert | `embedding_vectors`의 `processed_id + model_id` 기준 |
| 에러 이력 | append-only | 실패 이력 보존 |

## Idempotency 구현 패턴

### Check-First 패턴

```python
def idempotent_operation():
    # 1. 기존 데이터 확인
    existing = check_existing()
    if existing:
        return existing

    # 2. 새로 생성
    return create_new()
```

Cloudflare 봇 탐지 회피를 위해 크롤링은 `max_concurrent=1`, `batch_size=1`로 순차 실행한다.
동시 쓰기가 발생하지 않으므로 INSERT 충돌 가능성이 없어 Check-First 패턴으로 충분하다.
병렬 크롤링을 도입할 경우 upsert/conflict-handling 패턴으로 전환이 필요하다.

## Processing Rules

- `RetryableError`는 Airflow가 retry할 수 있도록 상위로 전파한다.
- 외부 라이브러리 예외는 서비스 경계에서 `RetryableError` 또는 `PermanentError`로 변환한다.
- item 단위 `PermanentError`는 `error_history`에 기록하고 다음 item을 처리한다.
- batch 전체 진행이 불가능한 `PermanentError`는 명확히 실패 처리한다.
- 재실행 대상은 DB 상태를 기준으로 선별한다.

## Consequences

- 모든 서비스 함수는 실패의 범위가 item 단위인지 batch 단위인지 명확히 해야 한다.
- 실패 이력 기록은 best effort가 아니라 운영 추적에 필요한 핵심 기능으로 다룬다.
- 임계값과 멱등성 키는 DB 스키마와 함께 유지되어야 한다.

## Related ADRs

- [ADR-004: DB Schema and State Model](004-db-schema-and-state-model.md)
- [ADR-006: TaskFlow API](006-taskflow-api.md)
