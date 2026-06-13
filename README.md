# JazzmateShop

재즈 감상문을 작성하면 AI가 유사한 앨범을 추천해주는 서비스.

AllAboutJazz 리뷰를 수집·요약·임베딩한 데이터를 기반으로, 사용자 감상문과 유사한 앨범을 비동기 AI 추천으로 제공한다.

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
| 백엔드 | Spring Boot 3 (Java) + FastAPI (Python) |
| 프론트엔드 | React |
| 컨테이너 | Docker Compose |

## 아키텍처

**서비스 흐름**
```
Browser
  ▼ :80
[nginx]
  ├── /**       → React static (SPA)
  └── /api/**   → Spring Boot :8080
                      └── FastAPI :8000 (내부 전용)
                              └── Supabase PostgreSQL
```

**데이터 파이프라인 (Airflow)**
```
DAG 1: URL 수집 → 크롤링 → GPT Batch 제출
         ↓ (TriggerDagRunOperator)
DAG 2: GPT Batch 완료 대기 (Sensor) → 결과 처리 → Embedding Batch 제출
         ↓ (TriggerDagRunOperator)
DAG 3: Embedding Batch 완료 대기 (Sensor) → 벡터 저장 (pgvector)
```

## 개발 환경 실행

각 서비스를 로컬에서 직접 실행한다.

**frontend**
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

**Java backend**
```
IDE에서 backendJava 프로젝트 실행 (IntelliJ 권장)
# http://localhost:8080
```

**Python AI API**
```bash
cd backendPython
uvicorn app.main:app --reload   # http://localhost:8000
```

환경변수는 `.env.example`을 참고해 각 서비스에 맞게 설정한다.

## 운영 전 리허설 (Docker Compose)

전체 스택을 Docker로 띄워 운영 환경과 동일하게 검증한다.

```bash
cp .env.example .env   # 실제 값으로 수정
docker compose up --build
# http://localhost:80
```

> 상세 인프라 설계 및 환경별 비교: [docs/infra/DEPLOY.md](docs/infra/DEPLOY.md)

## DB 마이그레이션

`pipeline/migrations/`, `backendJava/migrations/` 폴더의 SQL 파일을 Supabase 대시보드에서 순서대로 실행한다.

## 설계 결정 (ADR)

설계 결정은 영역별 ADR 문서에서 관리한다.

- 파이프라인 ADR: [docs/pipeline/adr/](docs/pipeline/adr/)
- Java 백엔드 ADR: [docs/backendJava/adr/](docs/backendJava/adr/)
- Python 백엔드 ADR: [docs/backendPython/adr/](docs/backendPython/adr/)
- 프론트엔드 ADR: [docs/frontend/adr/](docs/frontend/adr/)
