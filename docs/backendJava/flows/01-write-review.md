# [Java] 감상문 작성 + AI 추천 요청

> 전체 플로우: [docs/flows/01-write-review.md](../../../flows/01-write-review.md)

## 요구사항

- 감상문을 DB에 저장한다.
- 트랜잭션 커밋 후 `RecommendationEventListener`가 `@Async` + `AFTER_COMMIT`으로 FastAPI를 호출한다.
- AI 요청 실패해도 감상문 저장 트랜잭션에 영향 없음 — `AiRecommendationClient` 내부에서 catch, 로그만 기록.

## 테스트 시나리오

### `DtoFactoryTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 추천 목록 비어있음 → 상세 응답 DTO 분기 | review 객체 존재, hasRecommendations=false, recommendations=[] | `from_emptyRecommendations_hasRecommendationsFalse` |
| 추천 목록 있음 → 상세 응답 DTO 중첩 변환 | review 객체 존재, hasRecommendations=true, recommendations[0] 필드 매핑 | `from_withRecommendations_hasRecommendationsTrue` |
| 감상문 목록용 DTO 필드 매핑 | 목록 전용 8개 필드만 매핑 | `from_mapsOnly8Fields` |
| ApiResponse 성공 팩토리 | success=true, message, data 세팅 | `ok_withData_setsSuccessTrueAndData` |
| ErrorResponse 생성 | success=false 고정, message 세팅 | `errorResponse_successAlwaysFalse` |

### `UserReviewServiceTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 유효한 요청 → DB 저장 1회, 응답에 id 포함 | id 포함 UserReviewCreateResponse | `create_success_returnsResponseWithId` |
| 저장 후 이벤트 payload 검증 (reviewId, reviewContent) | event.reviewId == saved.id | `create_publishesRecommendationRequestEvent` |
| Builder 기본값 검증 | isFeatured=false, likeCount=0, commentCount=0 | `create_builderDefaultValues` |

### `UserReviewControllerTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| trackName 누락 → HTTP 400 | success=false | `create_missingTrackName_returns400` |
| artistName 누락 → HTTP 400 | success=false | `create_missingArtistName_returns400` |
| reviewContent 누락 → HTTP 400 | success=false | `create_missingReviewContent_returns400` |

### `GlobalExceptionHandlerTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| @Valid 실패 → 400, success=false, message 존재 | success=false, message 포함 | `validationError_returns400` |

### `RecommendationEventListenerTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| RecommendationRequestEvent 수신 → AiRecommendationClient 정확한 파라미터로 1회 호출 | client.requestRecommendation(reviewId, reviewContent) times(1) | `requestRecommendation_delegatesToClient` |

### Playwright

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 성공 경로 (저장 → 응답 data.id → navigate) | E2E 검증 | - |

### 추후 추가

| 대상 | 시나리오 | 기댓값 |
|------|----------|--------|
| `AiRecommendationClientTest` | FastAPI HTTP 클라이언트 구현 후 호출 실패 처리 검증 | 예외 전파 없음, 로그만 기록 |

## 구현 흐름

**감상문 저장**

`UserReviewController`
→ `UserReviewService`
→ `UserReviewRepository`

- `UserReviewController`: `POST /api/user-reviews` 수신, `@Valid` 검증, 응답 래핑
- `UserReviewService`: 감상문 생성, 저장 요청, 추천 요청 이벤트 발행
- `UserReviewRepository`: 감상문 저장

**커밋 후 AI 요청**

`RecommendationEventListener`
→ `AiRecommendationClient`

- `RecommendationEventListener`: `AFTER_COMMIT` + `@Async`로 AI 요청 시작
- `AiRecommendationClient`: FastAPI 호출, 실패 시 내부 catch

API/DTO/Entity 상세는 [API_SPEC.md](../../API_SPEC.md), [DB_SPEC.md](../DB_SPEC.md)를 따른다.
