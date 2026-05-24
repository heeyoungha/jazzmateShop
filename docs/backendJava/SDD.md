# JazzmateShop — Java 백엔드 설계 (SDD)

> - 버전: 4.0 | 날짜: 2026-05-23
> - 코딩 컨벤션 및 Best Practice: `AGENTS.md — Java 백엔드 코딩 컨벤션` 참조
> - 공통 설계 (인프라 라우팅 · API 계약 · 추천 상태 전이): [docs/SDD.md](../SDD.md)

---

## 목차

1. [레이어 책임 경계](#1-레이어-책임-경계)
2. [사용자 플로우별 설계](#2-사용자-플로우별-설계)
3. [참조 문서](#3-참조-문서)

---

## 1. 레이어 책임 경계

| 레이어 | 책임 | 금지 |
|--------|------|------|
| Controller | 입력 역직렬화<br>`@Valid` 검증<br>응답 포맷 결정 | try-catch (예외는 GlobalExceptionHandler로 전파)<br>비즈니스 로직<br>Repository 직접 접근 |
| Service | 비즈니스 로직<br>트랜잭션 경계<br>도메인 예외 직접 throw | `catch-rethrow` (`throw new RuntimeException(e)` 형태)<br>HTTP 통신 (→ Client에 위임) |
| Client | 외부 API HTTP 통신 전담 — 실패가 메인 트랜잭션에 영향을 주면 안 되므로 내부 catch 허용 | - |
| Repository | JPA 쿼리<br>Pageable 기반 페이징 | 비즈니스 로직 |
| Entity | DB 매핑<br>도메인 메서드 | - |
| DTO | 계층 간 데이터 전달<br>`static from()` 팩토리 메서드 | - |
| GlobalExceptionHandler | 모든 예외 중앙 처리<br>일관된 에러 응답 | - |

---

## 2. 사용자 플로우별 설계

| 페이지 | 포함 플로우 | 전체 플로우 | Java 구현 상세 |
|--------|-------------|------------|---------------|
| WriteReviewPage | 감상문 작성, 저장 후 AI 추천 요청 | [flows/01-write-review.md](../../flows/01-write-review.md) | [flows/01-write-review.md](./flows/01-write-review.md) |
| ReviewBasedRecommendPage | polling 상태 조회, 추천 콜백 수신, 결과 조회, 재시도 | [flows/02-recommend.md](../../flows/02-recommend.md) | [flows/02-recommend.md](./flows/02-recommend.md) |
| MyReviewsPage | 공개 감상문 목록 조회 | [flows/03-my-reviews.md](../../flows/03-my-reviews.md) | [flows/03-my-reviews.md](./flows/03-my-reviews.md) |
| CriticsReviewPage | 전문가 리뷰 목록/상세 조회 | [flows/04-critics-review.md](../../flows/04-critics-review.md) | [flows/04-critics-review.md](./flows/04-critics-review.md) |

---

## 3. 참조 문서

| 문서 | 역할 |
|------|------|
| [docs/SDD.md](../SDD.md) | 3 에이전트 공통 설계 기준 |
| [flows/](./flows/) | 플로우별 Java 구현 상세 |
| [DB_SPEC.md](./DB_SPEC.md) | DB · Entity · DTO 명세 |
| [API_SPEC.md](../API_SPEC.md) | 전체 API 명세 |
| [ADR-BJ001](./adr/001-test-strategy.md) | 테스트 전략 결정 |
| [ADR-BJ002](./adr/002-backend-design.md) | Java 백엔드 설계 결정 |
| [ADR-BJ003](./adr/003-realtime-notification-strategy.md) | AI 추천 상태 확인 방식 결정 |
| [Polling → SSE 전환 노트](./migration-notes/polling-to-sse.md) | 향후 SSE 전환 시 수정 지점과 체크리스트 |
