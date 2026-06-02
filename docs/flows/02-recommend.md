# 플로우 02 — AI 추천 처리 + Polling 결과 조회 + 재시도

## 전체 흐름

```
[프론트엔드]                  [Spring Boot]                    [FastAPI]
     │                             │                               │
     │         (플로우 01에서 이어짐 — navigate(/recommend/{id}) 직후)   │
     │                             │                               │
     │  GET /api/user-reviews/{id} │                               │
     │────────────────────────────►│                               │
     │  PENDING                    │                               │
     │◄────────────────────────────│                               │
     │                             │  POST /recommend/by-review    │
     │                             │──────────────────────────────►│
     │                             │                               │ 임베딩 생성
     │                             │                               │ 유사도 검색
     │                             │                               │ 추천 사유 생성
     │                             │  POST /api/user-reviews       │
     │                             │      /{id}/recommendations    │
     │                             │◄──────────────────────────────│
     │                             │  status == COMPLETED          │
     │                             │  recommend_album 저장          │
     │                             │                               │
     │  GET /api/user-reviews/{id} │                               │
     │  (polling 반복)              │                               │
     │────────────────────────────►│                               │
     │  COMPLETED + recommendations[]                              │
     │◄────────────────────────────│                               │
```

## 실패 콜백 흐름

```
[Spring Boot]                    [FastAPI]
     │                               │
     │  POST /recommend/by-review    │
     │──────────────────────────────►│
     │                               │ 임베딩/검색 실패
     │                               │ 또는 추천 후보 0건
     │  POST /api/user-reviews       │
     │      /{id}/recommendations    │
     │  { status: "FAILED", ... }    │
     │◄──────────────────────────────│
     │  status = FAILED              │
```

## 재시도 흐름 (FAILED 상태)

```
[프론트엔드]                  [Spring Boot]                    [FastAPI]
     │                             │                               │
     │  GET /api/user-reviews/{id} │                               │
     │────────────────────────────►│                               │
     │  recommendationStatus       │                               │
     │  == "FAILED"                │                               │
     │◄────────────────────────────│                               │
     │  retry 버튼 노출              │                               │
     │                             │                               │
     │  POST /api/user-reviews     │                               │
     │      /{id}/retry            │                               │
     │────────────────────────────►│                               │
     │                             │  PENDING 전이                  │
     │                             │  RecommendationRequestEvent   │
     │                             │  재발행                         │
     │                             │──────────────────────────────►│ (위 흐름 반복)
     │  이후 polling 재개            │                               │
```

## 모듈별 역할

| 모듈 | 상세 문서 |
|------|-----------|
| 프론트엔드 | [frontend/flows/02-recommend.md](../frontend/flows/02-recommend.md) |
| Spring Boot | [backendJava/flows/02-recommend.md](../backendJava/flows/02-recommend.md) |
| FastAPI | [backendPython/flows/02-recommend.md](../backendPython/flows/02-recommend.md) |

## 핵심 계약

- 프론트는 `GET /api/user-reviews/{id}` 응답의 `recommendationStatus`로 분기한다.
- `PENDING` → 대기 UI 유지 + polling 지속
- `COMPLETED` → `recommendations[]` 카드 렌더링 + polling 중단
- `FAILED` → 에러 메시지 + retry 버튼 노출 + polling 중단
- FastAPI는 처리 성공/실패 모두 `POST /api/user-reviews/{reviewId}/recommendations`로 콜백한다.
- retry는 `POST /api/user-reviews/{id}/retry`에서만 수행한다.
- GET 조회에서 `FAILED` 상태를 자동 재시도하지 않는다.

## 관련 API

- [API_SPEC.md — GET /api/user-reviews/{id}](../API_SPEC.md#get-apiuser-reviewsid)
- [API_SPEC.md — POST /api/user-reviews/{id}/retry](../API_SPEC.md#post-apiuser-reviewsidretry)
- [API_SPEC.md — POST /api/user-reviews/{reviewId}/recommendations](../API_SPEC.md#post-apiuser-reviewsreviewidrecommendations)
