# 파이프라인 규칙

> 적용 범위: `pipeline/` 디렉터리 (Python/Airflow DAG, 크롤러, 파이프라인 서비스)
> 공통 규칙: [루트 AGENTS.md](../AGENTS.md)

---

## 기술 스택

| 역할 | 기술 |
|---|---|
| 파이프라인 오케스트레이션 | Apache Airflow 2.8 (CeleryExecutor) |
| 크롤러 | Playwright (Chromium) |
| AI 요약 | OpenAI GPT Batch API (`gpt-4o-mini`) |
| AI 임베딩 | OpenAI Embedding Batch API (`text-embedding-3-small`, dim=1536) |
| 메시지 브로커 | Redis 7.2 |
| 알림 | Slack Webhook |

---

## 설계 기준 (ADR)

구현 변경 시 아래 ADR을 우선 확인한다.

| ADR | 주제 | 언제 확인할지 |
|---|---|---|
| [ADR-001](../docs/pipeline/adr/001-overall-architecture.md) | 전체 아키텍처 | 전체 파이프라인 구조, 기술 스택 변경 시 |
| [ADR-002](../docs/pipeline/adr/002-airflow-celery-executor.md) | CeleryExecutor 선택 | Airflow 실행기, worker, Redis 구성 변경 시 |
| [ADR-003](../docs/pipeline/adr/003-dag-pipeline-structure.md) | 3-DAG 파이프라인 구조 | DAG 구조, 트리거, Batch 대기 방식 변경 시 |
| [ADR-004](../docs/pipeline/adr/004-db-schema-and-state-model.md) | DB 스키마 | 테이블, 관계, 상태 저장 방식 변경 시 |
| [ADR-005](../docs/pipeline/adr/005-failure-idempotency-strategy.md) | 부분 실패와 멱등성 | 성공률 임계값, 재실행, upsert 정책 변경 시 |
| [ADR-006](../docs/pipeline/adr/006-taskflow-api.md) | TaskFlow API | DAG task 작성 방식, XCom 사용 방식 변경 시 |

---

## 환경 설정

```bash
# 로컬 개발 환경 시작
docker compose -f docker-compose.airflow.yaml up

# Airflow 웹 UI
http://localhost:8080  # airflow / airflow

# Celery 모니터링 (Flower)
docker compose -f docker-compose.airflow.yaml --profile flower up
http://localhost:5555
```

필수 환경변수 (`.env`):
- `OPENAI_API_KEY`
- `SUPABASE_URL`, `SUPABASE_KEY`
- `SLACK_WEBHOOK_URL`
- `AIRFLOW_UID`

---

## 역할 분리

| 에이전트 | 담당 영역 |
|---|---|
| Orchestrator | 태스크 분해, 결과 통합, 실패 판단 |
| Crawler Agent | Playwright 크롤링, URL 수집 |
| Pipeline Agent | OpenAI Batch 제출/폴링, Supabase 저장 |

---

## 에이전트 간 인터페이스

- 데이터 교환은 Supabase `pipeline_batches` 테이블을 single source of truth로 사용
- 에이전트는 직접 서로를 호출하지 않음 — 반드시 상태 테이블을 통해 핸드오프
- 태스크 결과는 XCom이 아닌 DB에 기록 (XCom 크기 제한 우회)

---

## 실패 처리 원칙

- `RetryableError` → 재시도 위임 (Airflow or Codex retry 정책 준수)
- `PermanentError` → `error_history` 기록 후 계속 진행 (부분 실패 허용)
- 80% 성공률 미달 시 전체 파이프라인 중단

---

## 코딩 컨벤션

**타입 안정성**
- 공개 함수와 서비스 메서드는 타입 힌트와 반환 타입을 명시한다.
- `Any`는 외부 API 응답, 점진적 마이그레이션 등 불가피한 경우로 제한한다.
- 외부 API 응답, DB row, DAG task 입출력처럼 경계가 있는 데이터는 Pydantic `BaseModel` 등 명시적 스키마를 사용한다.

**구조**
- `pipeline_services/`: 외부 API 클라이언트, DB 접근, 배치 처리 등 DAG에 독립적인 서비스 레이어
- `dags/crawling/`: Playwright 기반 크롤링 실행 모듈
    - Airflow worker 컨테이너와 로컬 실행에서 import 경로가 깨지지 않도록 유지한다.
    - DB 연동은 직접 SQL보다 `pipeline_services`의 서비스 계층을 우선 사용한다.
- DAG 파일(`.py`)에는 오케스트레이션만 작성하고, 비즈니스 로직은 `pipeline_services/` 또는 `dags/crawling/` 모듈에 둔다.

**비동기**
- 비동기 코드는 `async/await` 흐름을 일관되게 유지한다.
- Airflow Task 안에서 async 코드를 실행할 때는 `async_runner.py`의 유틸리티를 사용한다.

**설정**
- 환경변수는 설정 모듈에서 중앙 관리하고, 코드에 값을 하드코딩하지 않는다.
- `.env` 파일은 로컬 실행용 입력으로만 사용하며 코드에서 직접 수정하지 않는다.
- 크롤링 관련 설정은 `dags/crawling/core/config.py`에서 관리한다.

**예외 처리**
- 도메인/파이프라인 경계에서는 `exceptions.py`의 커스텀 예외 계층을 사용한다.
- 외부 라이브러리 예외는 필요한 위치에서 catch한 뒤 `RetryableError` 또는 `PermanentError`로 변환한다.
- `RetryableError`는 Airflow 재시도를 위해 상위로 전파한다.
- item 단위 부분 실패가 가능한 경우 `PermanentError`는 `error_history`에 기록하고 계속 진행한다.
- batch 전체를 진행할 수 없는 영구 오류는 명확히 실패 처리한다.

**네이밍**

| 대상 | 규칙 |
|---|---|
| 변수/함수 | `snake_case` |
| 클래스 | `PascalCase` |
| 상수 | `UPPER_SNAKE_CASE` |
| 파일 | `snake_case.py` |
| DAG 파일 | `{번호}_{역할}_dag.py` |
