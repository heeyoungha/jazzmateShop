# ADR-004: DB Schema and State Model

## Context

파이프라인은 여러 DAG와 외부 API Batch 작업으로 나뉘며, 각 단계의 상태와 결과를 안정적으로 추적해야 한다.

Airflow XCom은 대용량 데이터 저장에 적합하지 않다. 크롤링 결과, GPT 요약, 임베딩 메타데이터, 실패 이력은 외부 저장소에 기록해야 한다.

## Decision

Supabase/PostgreSQL을 파이프라인 상태와 결과의 single source of truth로 사용한다.

URL, 배치 실행, 크롤링 작업, 크롤링 결과를 분리해서 저장한다.

- `crawl_targets`는 프로젝트가 발견한 모든 목표 URL의 마스터 테이블로 둔다.
- `pipeline_batches`는 한 번의 파이프라인 실행 단위를 나타낸다.
- `crawl_jobs`는 특정 batch에서 어떤 target URL을 크롤링할지 관리하는 큐 역할을 한다.
- `allthatjazz_raw`는 크롤링이 성공한 원시 결과를 저장한다.

마이그레이션 파일은 `migrations/*.sql`에 두며, Supabase에 직접 실행하는 파일이므로 자동 수정하지 않는다.

## Rationale

이 구조의 핵심 목적은 중복 크롤링 방지, 배치 단위 추적, 재실행 가능성 확보이다.

`crawl_targets`는 AllAboutJazz에서 수집한 모든 리뷰 URL을 관리하는 URL 마스터다. 
URL은 여러 실행에서 다시 발견될 수 있으므로, URL 자체를 task 실행 결과와 분리해 저장한다. 
이를 통해 프로젝트가 이미 알고 있는 URL과 새로 발견한 URL을 구분하고, 같은 리뷰를 반복해서 크롤링하는 일을 줄일 수 있다.

`pipeline_batches`는 파이프라인 실행 단위를 관리한다. 
DAG run마다 하나의 batch를 만들고, 이후 크롤링, GPT Batch, Embedding Batch 작업은 이 batch를 기준으로 묶인다. 
batch 단위가 있어야 특정 실행의 진행률, 실패율, 후속 Batch 작업을 일관되게 추적할 수 있다.

`crawl_jobs`는 `pipeline_batches`와 `crawl_targets`를 연결하면서 실제 크롤링 큐 역할을 한다. 
같은 URL이라도 어느 batch에서 처리 대상이 되었는지, 현재 상태가 `pending`, `running`, `success`, `failed`, `skipped` 중 무엇인지 이 테이블에서 관리한다. 
Airflow task가 재시도되거나 중단 후 재개될 때도 `crawl_jobs` 상태를 기준으로 남은 작업만 다시 처리한다.

`allthatjazz_raw`는 크롤링이 성공한 원시 리뷰 데이터를 저장한다. 
크롤링 실행 상태는 `crawl_jobs`에 남기고, 실제 결과 payload는 `allthatjazz_raw`에 분리해 저장한다. 
이 분리 덕분에 실패한 job과 성공한 결과를 명확히 구분할 수 있고, GPT 요약 단계는 성공적으로 저장된 raw 데이터만 대상으로 삼을 수 있다.

## Tables

| 테이블 | 역할 |
|---|---|
| `crawl_targets` | URL 마스터. 프로젝트가 발견한 모든 목표 URL 관리 및 URL 중복 방지 |
| `pipeline_batches` | 파이프라인 실행 단위. DAG run과 후속 Batch 작업을 묶는 기준 |
| `crawl_jobs` | 배치별 크롤링 큐. `batch_id + crawl_target_id`로 실행 대상과 상태 관리 |
| `allthatjazz_raw` | 크롤링 성공 후 저장되는 원시 리뷰 결과 |
| `processed_summary` | GPT 요약 결과 |
| `processing_jobs` | OpenAI Batch 작업 상태 |
| `embedding_vectors` | 임베딩 메타데이터 |
| `error_history` | 통합 에러 이력 |
| `ai_models` | AI 모델 메타데이터 |
| `api_usage_logs` | API 사용량 로그 |

## Relationships

```text
pipeline_batches
    ├── crawl_jobs (batch_id FK)
    │       └── allthatjazz_raw (crawl_job_id FK, 1:1)
    │               └── processed_summary (raw_id FK, 1:1)
    │                       └── embedding_vectors (processed_id FK)
    └── processing_jobs (batch_id FK)

error_history
    ├── crawl_jobs (crawl_job_id FK, nullable)
    └── processing_jobs (processing_job_id FK, nullable)
```

## State Model

`pipeline_batches`는 배치 실행 단위의 기준이 된다. 에이전트와 DAG는 이 테이블을 기준으로 현재 실행 컨텍스트를 찾는다.

`crawl_jobs`는 크롤링 대상별 상태 머신 역할을 한다.

```text
pending -> running -> success
                 \-> failed
```

`processing_jobs`는 GPT, embedding, vectordb 등 외부 Batch 작업의 상태를 기록한다.

## Key Design Points

- `pipeline_batches.batch_num`은 시퀀스 기반 배치 번호로 동시성을 보장한다.
- `processing_jobs.stage`는 `gpt`, `embedding`, `vectordb` 등 처리 단계를 구분한다.
- `embedding_vectors`는 `processed_id + model_id` 기준으로 중복 저장을 방지한다.
- `error_history`는 append-only로 관리한다.
- 각 테이블의 `updated_at`은 DB trigger로 갱신한다.

## Consequences

- DAG 간 큰 데이터 전달은 DB row ID 또는 batch ID로 대체한다.
- task 재시도와 수동 재실행은 DB 상태를 기준으로 멱등성을 보장해야 한다.
- 스키마 변경은 관련 서비스 레이어와 ADR을 함께 업데이트해야 한다.

## Related ADRs

- [ADR-003: DAG Pipeline Structure](003-dag-pipeline-structure.md)
- [ADR-005: Failure and Idempotency Strategy](005-failure-idempotency-strategy.md)
- [ADR-006: TaskFlow API](006-taskflow-api.md)
