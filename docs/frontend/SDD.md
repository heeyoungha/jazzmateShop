# JazzmateShop — 프론트엔드 설계 (SDD)

> - 코딩 컨벤션 및 Best Practice: [frontend/AGENTS.md](../../frontend/AGENTS.md) 참조
> - 공통 설계 (인프라 라우팅 · API 계약 · 추천 상태 전이): [docs/SDD.md](../SDD.md)

---

## 목차

1. [역할과 책임](#1-역할과-책임)
2. [사용자 플로우별 설계](#2-사용자-플로우별-설계)
3. [참조 문서](#3-참조-문서)

---

## 1. 역할과 책임

| 영역 | 책임 | 금지 |
|------|------|------|
| Page | 라우트 단위 데이터 요청<br>loading/error 상태 관리<br>화면 분기 | API 응답 필드 임의 변환<br>백엔드 상태 전이 직접 수행 |
| Component | 입력 폼, 카드, 버튼, 리스트 등 UI 렌더링 | 직접 API 호출 남발<br>라우팅 변경 |
| API Client | HTTP 요청/응답 타입 관리<br>공통 에러 파싱 | UI 상태 직접 변경 |
| Router | 클라이언트 라우팅<br>페이지 전환 | 서버 API 경로와 혼동 |

---

## 2. 사용자 플로우별 설계

| 페이지 | 포함 플로우 | 전체 플로우 | 프론트 구현 상세 |
|--------|-------------|------------|-----------------|
| `WriteReviewPage` | 감상문 작성, 저장 후 추천 페이지 이동 | [flows/01-write-review.md](../flows/01-write-review.md) | [flows/01-write-review.md](./flows/01-write-review.md) |
| `ReviewBasedRecommendPage` | polling 상태 조회, 추천 결과 렌더링, 재시도 | [flows/02-recommend.md](../flows/02-recommend.md) | [flows/02-recommend.md](./flows/02-recommend.md) |
| `MyReviewsPage` | 공개 감상문 목록 조회 | [flows/03-my-reviews.md](../flows/03-my-reviews.md) | [flows/03-my-reviews.md](./flows/03-my-reviews.md) |
| `CriticsReviewPage` | 전문가 리뷰 목록 조회 | [flows/04-critics-review.md](../flows/04-critics-review.md) | [flows/04-critics-review.md](./flows/04-critics-review.md) |
| `CriticsReviewDetailPage` | 전문가 리뷰 상세 조회 | [flows/04-critics-review.md](../flows/04-critics-review.md) | [flows/04-critics-review.md](./flows/04-critics-review.md) |

---

## 3. 참조 문서

| 문서 | 역할 |
|------|------|
| [docs/SDD.md](../SDD.md) | 공통 시스템 설계 기준 |
| [docs/API_SPEC.md](../API_SPEC.md) | 프론트가 호출하는 API 계약 |
| [flows/](./flows/) | 플로우별 프론트엔드 구현 상세 |
| [ADR-FE001](./adr/001-state-and-api-response.md) | 상태 소유와 API 응답 처리 결정 |
| [ADR-FE002](./adr/002-recommendation-polling-ui.md) | 추천 상태 polling UI 결정 |
| [ADR-FE003](./adr/003-frontend-test-strategy.md) | 프론트엔드 테스트 전략 결정 |
| [docs/infra/DEPLOY.md](../infra/DEPLOY.md) | SPA fallback, nginx, Spring Boot 라우팅 구조 |
