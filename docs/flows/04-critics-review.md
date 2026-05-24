# 플로우 04 — 전문가 리뷰 목록/상세 조회

## 전체 흐름

```
[프론트엔드]                  [Spring Boot]
     │                             │
     │  GET /api/critics           │
     │  ?page=0&size=10            │
     │────────────────────────────►│
     │                             │  reviewSummary 있는 것만 반환
     │  { content[], last, ... }   │
     │◄────────────────────────────│
     │  카드 렌더링                   │
     │  last==true → 스크롤 종료      │
     │                             │
     │  GET /api/critics/{id}      │
     │────────────────────────────►│
     │  CriticsReview              │
     │◄────────────────────────────│
```

## 모듈별 역할

| 모듈 | 역할 | 상세 문서 |
|------|------|-----------|
| 프론트엔드 | 목록 무한 스크롤, 상세 페이지 | [frontend/flows/04-critics-review.md](../frontend/flows/04-critics-review.md) |
| Spring Boot | GPT 요약 완료 리뷰 페이지네이션 조회 | [backendJava/flows/04-critics-review.md](../backendJava/flows/04-critics-review.md) |

## 핵심 계약

- `reviewSummary`가 있는 리뷰만 반환 (GPT 요약 완료 기준)
- `last == true` → 프론트 무한 스크롤 종료
- `number` → 다음 요청 시 `page=number+1`

## 관련 API

- [API_SPEC.md — GET /api/critics](../API_SPEC.md#get-apicritics)
- [API_SPEC.md — GET /api/critics/{id}](../API_SPEC.md#get-apicriticsid)
