# JazzmateShop — 공통 시스템 설계 (SDD)

> - 프론트엔드 · Spring Boot · FastAPI 에이전트가 공통으로 참조하는 설계 문서입니다.
> - 모듈별 구현 상세: 
>    - [backendJava/SDD.md](./backendJava/SDD.md)
>    - [frontend/SDD.md](./frontend/SDD.md)

## 문서 운영 원칙

- 이 문서는 JazzmateShop 구현에 필요한 설계 문서와 작업 기준을 안내한다.
- AI agent가 어느 시점에 어떤 모델로 구현하더라도 같은 구조와 품질 기준을 따르도록 설계 의도를 고정하는 것이 목적이다.
- 설계 변경이 필요한 경우 구현보다 문서를 먼저 수정하고 리뷰를 받는다.
- 테스트 시나리오에 없는 동작을 임의로 추가하지 않는다.

---

## 목차

1. [인프라 라우팅](#1-인프라-라우팅)
2. [API 계약 — 프론트 분기 로직 의존 필드](#2-api-계약--프론트-분기-로직-의존-필드)
3. [추천 상태 전이](#3-추천-상태-전이)

---

## 1. 인프라 라우팅

```
브라우저 → nginx → Spring Boot → FastAPI
```

| 경로 패턴 | 처리 |
|-----------|------|
| `/api/**` | Spring Boot API |
| `/ai-api/**` | Spring Boot가 prefix 제거 후 FastAPI로 프록시 |
| 그 외 모든 경로 | Spring Boot → `index.html` (SPA Fallback) |

- React Router가 클라이언트에서 실제 라우팅 처리 (`/recommend/:id` 등)
- FastAPI는 브라우저에서 직접 접근 불가 — 항상 Spring Boot를 통해 호출됨

---

## 2. API 계약 — 프론트 분기 로직 의존 필드

전체 API 명세: [API_SPEC.md](./API_SPEC.md)

프론트엔드가 분기 로직에 직접 사용하는 필드:

```
POST /api/user-reviews 응답:
  data.id  ← navigate(`/recommend/${data.id}`)에 사용, 누락 시 이동 불가

GET /api/critics 응답:
  last     ← true이면 무한 스크롤 종료
  number   ← 다음 요청 시 page=number+1

GET /api/user-reviews/{id} 응답:
  recommendationStatus  ← PENDING/COMPLETED/FAILED 프론트 상태 표시용
  recommendations[]     ← COMPLETED일 때 카드 렌더링 대상

Polling:
  recommendationStatus == PENDING   ← 일정 interval 후 GET /api/user-reviews/{id} 재호출
  recommendationStatus == COMPLETED ← recommendations[] 렌더링 후 중단
  recommendationStatus == FAILED    ← retry 버튼 노출 후 중단
```

---

## 3. 추천 상태 전이

`recommendationStatus` 필드는 프론트 UI 분기, FastAPI 콜백 처리, Spring 재시도 로직이 모두 의존한다.

```
PENDING (기본값, 감상문 저장 직후)
  → FastAPI 콜백 수신 + recommend_album 저장 완료  → COMPLETED
  → AI 요청 실패 또는 콜백 미수신                  → FAILED
  → FAILED 상태에서 POST /api/user-reviews/{id}/retry → PENDING (재시도)
```

| 상태 | Spring (상태 관리) | 프론트 (UI 분기) | FastAPI (처리 기준) |
|------|-------------------|-----------------|-------------------|
| `PENDING` | 감상문 저장 시 초기값 설정<br>FastAPI에 추천 요청 전송 | 대기 중 UI + polling 유지 | 추천 요청 수신 후 처리 시작 |
| `COMPLETED` | FastAPI 콜백 수신 후 전이 | `recommendations[]` 카드 렌더링 | 추천 결과 콜백 전송 완료 |
| `FAILED` | AI 요청 실패 시 전이<br>retry 요청 수신 시 PENDING으로 복귀 | 에러 메시지 + retry 버튼 노출 | - (관여 없음) |
