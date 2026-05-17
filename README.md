# AllAboutJazz 데이터 파이프라인

AllAboutJazz 재즈 리뷰를 수집하고, GPT 요약과 임베딩을 거쳐 Supabase에 저장하는 Airflow 기반 데이터 파이프라인.

## 프로젝트 바로가기                                                                      
                                                                                          
[https://actlog.shop/](https://actlog.shop/)   

## 기술 스택

| 역할 | 기술 |
|---|---|
| 파이프라인 오케스트레이션 | Apache Airflow 2.8 (CeleryExecutor) |
| 크롤러 | Playwright (Chromium) |
| AI 요약 | OpenAI GPT Batch API (`gpt-4o-mini`) |
| AI 임베딩 | OpenAI Embedding Batch API (`text-embedding-3-small`, dim=1536) |
| 관계형 DB | Supabase (PostgreSQL 16 + pgvector) |
| 메시지 브로커 | Redis 7.2 |
| 알림 | Slack Webhook |
| 컨테이너 | Docker Compose |

## 파이프라인 구조

3개의 DAG가 순차적으로 트리거되는 구조.

```
DAG 1: URL 수집 → 크롤링 → GPT Batch 제출
         ↓ (TriggerDagRunOperator)
DAG 2: GPT Batch 완료 대기 (Sensor) → 결과 처리 → Embedding Batch 제출
         ↓ (TriggerDagRunOperator)
DAG 3: Embedding Batch 완료 대기 (Sensor) → 벡터 저장
```

## 프로젝트 구조

```
jazzShop_202601/
├── dags/
│   ├── 1_crawl_dag.py
│   ├── 2_summary_dag.py
│   ├── 3_embedding_vector_dag.py
│   └── crawling/
│       ├── core/config.py
│       ├── crawlers/playwright_crawler.py
│       ├── services/resource_monitor.py
│       └── utils/
├── pipeline_services/
│   ├── exceptions.py
│   ├── superbase_service.py
│   ├── openai_service.py
│   ├── crawl_job_manager.py
│   └── async_runner.py
├── migrations/
├── docs/adr/
├── Dockerfile
├── docker-compose.yaml
├── AGENTS.md
└── CLAUDE.md
```

## 시작하기

### 필수 환경변수 (`.env`)

```
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
SLACK_WEBHOOK_URL=
AIRFLOW_UID=
```

### 실행

```bash
# 환경 시작
docker compose up

# Airflow 웹 UI
http://localhost:8080  # airflow / airflow

# Celery 모니터링 (Flower)
docker compose --profile flower up
http://localhost:5555
```

### DB 마이그레이션

`migrations/` 폴더의 SQL 파일을 Supabase 대시보드에서 순서대로 실행.

## 설계 결정 (ADR)

구조적 결정은 `docs/adr/`를 참고.

| ADR | 주제 |
|---|---|
| [001](docs/adr/001-overall-architecture.md) | 전체 아키텍처 |
| [002](docs/adr/002-airflow-celery-executor.md) | CeleryExecutor 선택 |
| [003](docs/adr/003-dag-pipeline-structure.md) | 3-DAG 파이프라인 구조 |
| [004](docs/adr/004-db-schema-and-state-model.md) | DB 스키마 |
| [005](docs/adr/005-failure-idempotency-strategy.md) | 부분 실패와 멱등성 |
| [006](docs/adr/006-taskflow-api.md) | TaskFlow API |
