# JazzmateShop — 전체 시스템 아키텍처

## 시스템 흐름

```
AllAboutJazz (외부)
    │
    │ 크롤링 (Playwright)
    ▼
[Airflow 파이프라인]
    │  DAG 1: URL 수집 + 크롤링
    │  DAG 2: GPT 요약 (Batch API)
    │  DAG 3: 임베딩 생성 및 저장
    ▼
Supabase (PostgreSQL)
    │  v_album_embeddings 뷰 (읽기 전용)
    ▼
[FastAPI AI 서버]  ←── POST /recommend/by-review  ←── [Spring Boot]
    │
    │ 추천 결과 콜백
    │ POST /api/user-reviews/{reviewId}/recommendations
    ▼
[Spring Boot 백엔드]  ←── polling GET /api/user-reviews/{id} ──→  브라우저 (React)
```

## 모듈별 역할

| 모듈 | 기술 | 역할 |
|------|------|------|
| pipeline | Airflow 2.8 + Playwright + OpenAI Batch API | 재즈 리뷰 수집 → GPT 요약 → 임베딩 저장 |
| backendJava | Spring Boot 3 (Java) | 감상문 저장, AI 추천 요청/수신, polling 상태 조회 응답 |
| backendPython | FastAPI | 임베딩 유사도 계산 및 추천 결과 콜백 |
| DB | Supabase (PostgreSQL 16) | 전체 데이터 저장소 |
| infra | Docker Compose + nginx | 컨테이너 오케스트레이션 및 리버스 프록시 |

## 문서 링크

| 영역 | 문서 |
|------|------|
| 공통 시스템 설계 | [docs/SDD.md](./SDD.md) |
| 사용자 플로우 | [docs/flows/](./flows/) |
| API 명세 | [docs/API_SPEC.md](./API_SPEC.md) |
| 파이프라인 | [docs/pipeline/](./pipeline/) |
| Java 백엔드 | [docs/backendJava/](./backendJava/) |
| Python 백엔드 | [docs/backendPython/](./backendPython/) |
| 프론트엔드 | [docs/frontend/](./frontend/) |
| 인프라 및 배포 | [docs/infra/DEPLOY.md](./infra/DEPLOY.md) |
