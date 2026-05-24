# 플로우 01 — 감상문 작성 + AI 추천 요청

## 전체 흐름

```
[프론트엔드]                  [Spring Boot]                    [FastAPI]
     │                             │                               │
     │  POST /api/user-reviews     │                               │
     │────────────────────────────►│                               │
     │                             │  - DB 저장 (user_reviews)      │
     │                             │  - RecommendationRequestEvent │
     │                             │  발행 (AFTER_COMMIT, @Async)   │
     │                             │                               │
     │                             │  POST /recommend/by-review    │
     │  navigate(/recommend/{id})  │  (@Async)                     │
     │◄────────────────────────────│──────────────────────────────►│
     │  201 { data.id }            │                               │
     │                             │                               │
```

## 모듈별 역할

| 모듈 | 역할 | 상세 문서 |
|------|------|-----------|
| 프론트엔드 | 감상문 폼 렌더링, POST 요청, `data.id`로 페이지 이동 | [frontend/flows/01-write-review.md](../frontend/flows/01-write-review.md) |
| Spring Boot | 감상문 저장, 커밋 후 FastAPI 비동기 호출 | [backendJava/flows/01-write-review.md](../backendJava/flows/01-write-review.md) |
| FastAPI | 추천 요청 수신 후 처리 시작 (→ 플로우 02로 이어짐) | [backendPython/flows/02-recommend.md](../backendPython/flows/02-recommend.md) |

## 핵심 계약

- `POST /api/user-reviews` 응답의 `data.id` — 프론트가 `/recommend/{id}`로 이동하는 데 사용
- AI 요청 실패는 감상문 저장 트랜잭션에 영향 없음 (비동기 분리)
- 저장 후 `recommendationStatus = PENDING` 상태로 시작

## 관련 API

- [API_SPEC.md — POST /api/user-reviews](../API_SPEC.md#post-apiuser-reviews)
- [API_SPEC.md — POST /recommend/by-review](../API_SPEC.md#post-recommendby-review)
