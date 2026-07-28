# JazzmateShop

재즈 감상문을 작성하면 AI가 유사한 앨범을 추천해주는 서비스.

AllAboutJazz 리뷰를 수집·요약·임베딩한 데이터를 기반으로, 사용자 감상문과 유사한 앨범을 비동기 AI 추천으로 제공한다.

## 프로젝트 바로가기                 
[https://actlog.shop/](https://actlog.shop/)   

## 개발 철학

SDD + TDD 기반으로 운영한다. AI 에이전트가 코드를 구현하고, 개발자는 설계와 검증에 집중한다.

상세: [docs/development-philosophy.md](docs/development-philosophy.md)

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
| 데이터 품질 대시보드 | Python + pandas + matplotlib/seaborn |
| 부하 테스트/관찰성 | k6 + Prometheus + Grafana |
| 컨테이너 | Docker Compose |

## 아키텍처

상세 설계: [docs/SDD.md](docs/SDD.md)

## 구현 모듈

| 경로 | 역할 |
|---|---|
| `frontend/` | React SPA. 감상문 작성, 추천 결과 polling, 내 감상문/평론 목록 UI |
| `backendJava/` | Spring Boot API. 감상문 저장, 추천 요청 발행, FastAPI callback 수신, 상태 조회 |
| `backendPython/` | FastAPI AI API. 감상문 임베딩, pgvector 유사도 검색, 추천 이유 생성, Spring callback |
| `pipeline/` | Airflow DAG. AllAboutJazz URL 수집, 리뷰 크롤링, GPT 요약 Batch, 임베딩 Batch 저장 |
| `dashboard/` | Supabase `allthatjazz_raw` 데이터 품질 분석 및 누락 필드 시각화 |
| `load-tests/` | polling 기준선, 추천 E2E 부하 테스트, mock AI API, Prometheus/Grafana 관찰 구성 |
| `nginx/` | 운영용 React static 서빙 및 `/api/**` Spring Boot 프록시 |
| `docs/` | 시스템 설계, API 명세, 영역별 ADR/flow 문서 |

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

## 데이터 품질 대시보드

`dashboard/data_quality_visualizer.py`는 Supabase의 `allthatjazz_raw` 테이블을 읽어 필드 누락률, 전체 품질 점수, 시계열 변화 추이를 생성한다.

```bash
cd dashboard
python data_quality_visualizer.py
```

생성/갱신 파일:

- `dashboard/data_quality_heatmap.png`
- `dashboard/data_quality_timeseries.png`
- `dashboard/data_quality_history.csv`

필요 환경변수:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## 부하 테스트

k6 기반 추천 E2E 부하 테스트. 상세: [load-tests/README.md](load-tests/README.md)

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

**ADR vs 규칙 문서 기준**

| 문서 종류 | 언제 쓰나 | 예시 |
|---|---|---|
| ADR | 특정 시점에 내린 결정, 배경, 트레이드오프를 기록한다. 나중에 "왜 이렇게 했나"를 추적하기 위한 것이므로 변경하지 않고 새 ADR로 덮는다. | CeleryExecutor 선택, DB 스키마 설계, 실패 전략 |
| 규칙 문서 | 지속적으로 따르는 컨벤션이나 가이드라인을 정의한다. 규칙이 바뀌면 문서를 직접 수정한다. | 다이어그램 종류 선택 기준, 코딩 컨벤션 |

규칙 문서: [docs/documentation-convention.md](docs/documentation-convention.md)
