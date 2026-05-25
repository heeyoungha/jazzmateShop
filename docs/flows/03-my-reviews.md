# 플로우 03 — 내 감상문 목록 조회

## 전체 흐름

```
[프론트엔드]                  [Spring Boot]
     │                             │
     │  GET /api/user-reviews      │
     │  ?page=0&size=10            │
     │────────────────────────────►│
     │                             │  isPublic=true 필터
     │                             │  createdAt DESC 정렬
     │  Page<UserReviewSummary>    │
     │◄────────────────────────────│
     │  카드 렌더링                   │
     │  last=false면 page+1 요청     │
```

## 모듈별 역할

| 모듈 | 역할 | 상세 문서 |
|------|------|-----------|
| 프론트엔드 | 목록 렌더링, 무한 스크롤 | [frontend/flows/03-my-reviews.md](../frontend/flows/03-my-reviews.md) |
| Spring Boot | 공개 감상문 페이지네이션 조회 | [backendJava/flows/03-my-reviews.md](../backendJava/flows/03-my-reviews.md) |

## 핵심 계약

- `isPublic=true`인 감상문만 반환
- 정렬: `createdAt` DESC
- `content[]`: 감상문 카드 렌더링 대상
- `last`: `true`이면 무한 스크롤 종료
- `number`: 다음 요청 시 `page=number+1`

## 관련 API

- [API_SPEC.md — GET /api/user-reviews](../API_SPEC.md#get-apiuser-reviews)
