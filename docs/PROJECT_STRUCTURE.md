# JazzmateShop — 전체 프로젝트 구조

> 이 파일은 파이프라인(Python/Airflow)과 백엔드(Java/Spring Boot) 모듈을 포함한 전체 구조를 단일 문서로 정리합니다.
> 코딩 컨벤션: `../../AGENTS.md` / DTO·Entity 명세: `DTO_SPEC.md` / 플로우 설계: `SDD.md`

---

## 전체 아키텍처

```
AllAboutJazz (외부)
    │
    │ 크롤링
    ▼
[Airflow 파이프라인]  ──→  Supabase (PostgreSQL)
    │                           │
    │ 임베딩 저장               │ v_album_embeddings 뷰
    ▼                           │
[FastAPI AI 서버]  ←──────────────
    │ 추천 콜백
    ▼
[Spring Boot 백엔드]  ←──→  프론트엔드 (React)
    │
    │ SSE
    ▼
  브라우저
```

---

## 디렉터리 구조

```
JazzmateShop/
│
├── pipeline/                       # Airflow 파이프라인 모듈
│   ├── dags/                       # Airflow DAG 및 크롤링 모듈
│   │   ├── 1_crawl_dag.py          # DAG 1: URL 수집 + 크롤링
│   │   ├── 2_summary_dag.py        # DAG 2: GPT 요약 (Batch API)
│   │   ├── 3_embedding_vector_dag.py  # DAG 3: 임베딩 생성 및 저장
│   │   ├── common/
│   │   │   └── slack.py            # Slack 알림 공통 유틸
│   │   └── crawling/               # Playwright 크롤링 모듈
│   │       ├── core/
│   │       │   └── config.py       # 크롤링 설정 (환경변수 중앙 관리)
│   │       ├── crawlers/
│   │       │   └── playwright_crawler.py
│   │       ├── services/
│   │       │   ├── crawl_job_service.py
│   │       │   ├── crawl_service.py
│   │       │   └── resource_monitor.py
│   │       └── utils/
│   │           ├── date_parser.py
│   │           ├── rate_limiter.py
│   │           └── validation.py
│   ├── pipeline_services/          # DAG에 독립적인 서비스 레이어
│   │   ├── crawl_job_manager.py    # 크롤링 작업 상태 관리
│   │   ├── openai_service.py       # OpenAI Batch API 클라이언트
│   │   ├── review_crawler_service.py  # 리뷰 크롤링 서비스
│   │   ├── superbase_service.py    # Supabase DB 접근
│   │   └── url_collector_service.py   # URL 수집 서비스
│   ├── config/
│   │   └── airflow.cfg
│   ├── migrations/                 # 파이프라인 마이그레이션 SQL (자동 수정 금지)
│   │   ├── 001_create_tables.sql
│   │   └── ...009_add_vector_column_to_embedding_vectors.sql
│   ├── requirements-base.txt
│   └── requirements-app.txt
│
├── backendJava/                    # Spring Boot 백엔드 모듈
│   ├── migrations/                 # Java 백엔드 마이그레이션 SQL (자동 수정 금지)
│   │   ├── 010_create_jazzmate_shop_tables.sql    # user_reviews, recommend_album
│   │   ├── 011_add_recommendation_status_to_user_reviews.sql
│   │   └── 012_create_v_album_embeddings.sql      # 추천 앨범 뷰
│   └── src/
│       ├── main/java/.../
│       │   ├── common/
│       │   │   ├── dto/
│       │   │   │   ├── ApiResponse.java        # 생성 성공 응답 래퍼
│       │   │   │   └── ErrorResponse.java      # 에러 응답 래퍼
│       │   │   └── exception/
│       │   │       ├── GlobalExceptionHandler.java
│       │   │       └── ResourceNotFoundException.java
│       │   ├── infrastructure/
│       │   │   ├── RecommendationEventListener.java  # AFTER_COMMIT + @Async
│       │   │   └── SseEmitterRegistry.java           # SSE 연결 관리
│       │   ├── userReview/
│       │   │   ├── UserReviewController.java   # (미구현)
│       │   │   ├── UserReviewService.java
│       │   │   ├── UserReviewRepository.java
│       │   │   ├── entity/
│       │   │   │   ├── UserReview.java
│       │   │   │   └── RecommendationStatus.java  # PENDING/COMPLETED/FAILED
│       │   │   └── dto/
│       │   │       ├── UserReviewRequest.java
│       │   │       ├── UserReviewResponse.java
│       │   │       └── UserReviewSummaryResponse.java
│       │   ├── recommendation/
│       │   │   ├── RecommendAlbumController.java  # (미구현)
│       │   │   ├── RecommendAlbumService.java
│       │   │   ├── RecommendAlbumRepository.java
│       │   │   ├── client/
│       │   │   │   └── AiRecommendationClient.java  # FastAPI HTTP 호출
│       │   │   ├── entity/
│       │   │   │   └── RecommendAlbum.java
│       │   │   ├── dto/
│       │   │   │   └── RecommendAlbumBatchRequest.java  # FastAPI 콜백 수신
│       │   │   └── event/
│       │   │       ├── RecommendationRequestEvent.java  # 감상문 저장 후 발행
│       │   │       └── RecommendationReadyEvent.java    # 추천 저장 후 발행 → SSE
│       │   └── criticsReview/                          # (미구현)
│       │       ├── CriticsReviewController.java
│       │       ├── CriticsReviewService.java
│       │       ├── CriticsReviewRepository.java
│       │       └── entity/
│       │           └── CriticsReview.java
│       └── test/java/.../
│           ├── dto/
│           │   └── DtoFactoryTest.java
│           ├── infrastructure/
│           │   ├── RecommendationEventListenerTest.java
│           │   └── SseEmitterRegistryTest.java
│           ├── recommendation/
│           │   ├── AiRecommendationClientTest.java
│           │   ├── RecommendAlbumControllerTest.java
│           │   └── RecommendAlbumServiceTest.java
│           ├── criticsReview/
│           │   └── CriticsReviewServiceTest.java
│           └── userReview/
│               ├── UserReviewControllerTest.java
│               ├── UserReviewRepositoryTest.java
│               └── UserReviewServiceTest.java
│
├── backendPython/                  # FastAPI AI 서버 (미구현)
│
├── docs/
│   ├── adr/                        # Architecture Decision Records
│   │   ├── 001-overall-architecture.md
│   │   ├── 002-airflow-celery-executor.md
│   │   ├── 003-dag-pipeline-structure.md
│   │   ├── 004-db-schema-and-state-model.md
│   │   ├── 005-failure-idempotency-strategy.md
│   │   ├── 006-taskflow-api.md
│   │   ├── 007-test-strategy.md
│   │   └── 008-recommendation-status.md
│   └── ref/                        # 참고 자료
│
├── config/
│   └── airflow.cfg
├── docker-compose.airflow.yaml     # Airflow + Redis + Worker 컨테이너
├── Dockerfile.airflow
│
├── AGENTS.md              # 공통 규칙 (코딩 컨벤션, 제약, 역할 분리)
├── CLAUDE.md              # Claude Code 전용 설정
├── CODEX.md               # Codex 전용 설정
└── docs/design/           # 설계 문서
    ├── PROJECT_STRUCTURE.md  # 이 파일
    ├── SDD.md             # 플로우 기반 설계 문서
    ├── DTO_SPEC.md        # DTO/Entity 필드 명세
    └── TDD.md             # 테스트 체크리스트
```

---

## 백엔드 패키지 구조

```
shop.jazzmate.jazzmateshop
│
├── common/
│   ├── dto/           ApiResponse<T>, ErrorResponse
│   └── exception/     ResourceNotFoundException
│
├── infrastructure/
│   └──                SseEmitterRegistry
│
├── userReview/
│   ├──                UserReviewController  (미구현)
│   ├──                UserReviewService
│   ├──                UserReviewRepository
│   ├── entity/        UserReview, RecommendationStatus
│   └── dto/           UserReviewRequest, UserReviewResponse, UserReviewSummaryResponse
│
├── recommendation/
│   ├──                RecommendAlbumController  (미구현)
│   ├──                RecommendAlbumService
│   ├──                RecommendAlbumRepository
│   ├── entity/        RecommendAlbum
│   ├── dto/           RecommendAlbumBatchRequest
│   └── event/         RecommendationRequestEvent, RecommendationReadyEvent
│
└── criticsReview/     (미구현)
    ├──                CriticsReviewController
    ├──                CriticsReviewService
    ├──                CriticsReviewRepository
    └── entity/        CriticsReview
```

### 패키지 편성 원칙

- **도메인 중심 패키지** (`userReview/`, `recommendation/`, `criticsReview/`): 도메인별로 Controller/Service/Repository/Entity/DTO를 함께 묶음
- **공통 패키지** (`common/`): 특정 도메인에 종속되지 않는 DTO와 예외
- **인프라 패키지** (`infrastructure/`): Spring 기반 인프라 컴포넌트 (SSE, 이벤트 리스너 등)
- **이벤트 패키지** (`event/`): 도메인 이벤트 Record — 발행자와 수신자가 다른 패키지에 있을 때 순환 의존 방지

---

## DB 테이블 / 뷰

| 이름 | 종류 | 설명 |
|------|------|------|
| `user_reviews` | 테이블 | 사용자 감상문 (migration 010) |
| `recommend_album` | 테이블 | AI 추천 앨범 결과 (migration 010) |
| `embedding_vectors` | 테이블 | 임베딩 벡터 (파이프라인 저장) |
| `allthatjazz_raw` | 테이블 | 크롤링 원문 데이터 |
| `v_review_summary` | 뷰 | 전문가 리뷰 + GPT 요약 (CriticsReview Entity) |
| `v_album_embeddings` | 뷰 | embedding_vectors + allthatjazz_raw JOIN (migration 012) |

> `v_album_embeddings.album_id` = `embedding_vectors.id` — FastAPI가 추천 시 반환하는 albumId의 기준

---

## 데이터 파이프라인 흐름

```
DAG 1 (크롤링)
  collect_urls → crawl_reviews → save_to_supabase
        ↓
DAG 2 (GPT 요약)
  fetch_pending → submit_batch → poll_batch → save_summaries
        ↓
DAG 3 (임베딩)
  fetch_pending → submit_batch → poll_batch → save_embeddings
        ↓
  Supabase: embedding_vectors + v_album_embeddings 뷰 생성
```

---

## 백엔드 API 흐름

```
프론트엔드
  │
  ├── POST /api/user-reviews                         UserReviewController
  │     → UserReviewService.createUserReview()
  │     → 이벤트 발행 (AFTER_COMMIT)
  │     → FastAPI POST /recommend
  │
  ├── GET  /api/user-reviews                         UserReviewController
  ├── GET  /api/user-reviews/{id}                    UserReviewController
  ├── GET  /api/user-reviews/{id}/sse                UserReviewController (SSE)
  │
  ├── POST /api/user-reviews/{id}/recommendations    RecommendAlbumController
  │     ← FastAPI 콜백 (추천 결과 저장)
  │     → SSE emit "recommendation-ready"
  │
  └── GET  /api/critics-reviews                      CriticsReviewController
      GET  /api/critics-reviews/{id}                 CriticsReviewController
```
