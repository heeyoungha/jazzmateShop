# [Java] 감상문 작성 + AI 추천 요청

> 전체 플로우: [docs/flows/01-write-review.md](../../../flows/01-write-review.md)

## 요구사항

- 감상문을 DB에 저장한다.
- 트랜잭션 커밋 후 `RecommendationEventListener`가 `@Async` + `AFTER_COMMIT`으로 FastAPI를 호출한다.
- AI 요청 실패해도 감상문 저장 트랜잭션에 영향 없음 — `AiRecommendationClient` 내부에서 catch, 로그만 기록.

## 테스트 시나리오

### DTO — [`DtoFactoryTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/dto/DtoFactoryTest.java)

| 시나리오 |
|----------|
| 추천 목록이 비어 있으면 상세 응답 DTO에서 `hasRecommendations=false` 반환 |
| 추천 목록이 있으면 상세 응답 DTO에서 추천 목록을 중첩 DTO로 변환 |
| 감상문 목록용 DTO는 목록 전용 필드만 매핑 |
| `ApiResponse` 성공 응답 생성 |
| `ApiResponse` 성공 응답 생성 시 data 생략 |
| `ErrorResponse` 생성 시 실패 응답 형식 유지 |

### Service — [`UserReviewServiceTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java)

| 시나리오 |
|----------|
| 유효한 감상문 요청을 저장하고 생성 응답에 id 포함 |
| 감상문 저장 후 추천 요청 이벤트 발행 |
| 감상문 생성 시 builder 기본값 적용 |

### Controller — [`UserReviewControllerTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewControllerTest.java)

| 시나리오 |
|----------|
| 저장 성공 시 HTTP 201과 `data.id` 포함 응답 반환 |
| `trackName` 누락 시 HTTP 400 반환 |
| `artistName` 누락 시 HTTP 400 반환 |
| `reviewContent` 누락 시 HTTP 400 반환 |

### Exception — [`GlobalExceptionHandlerTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/GlobalExceptionHandlerTest.java)

| 시나리오 |
|----------|
| `@Valid` 실패 시 HTTP 400과 실패 응답 반환 |
| `ResourceNotFoundException` 발생 시 HTTP 404와 실패 응답 반환 |
| 예상하지 못한 예외 발생 시 HTTP 500과 실패 응답 반환 |

### Event — [`RecommendationEventListenerTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/infrastructure/RecommendationEventListenerTest.java)

| 시나리오 |
|----------|
| `RecommendationRequestEvent` 수신 시 `AiRecommendationClient`에 추천 요청 위임 |

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

API/DTO/Entity 상세는 [API_SPEC.md](../../API_SPEC.md), [MODEL_SPEC.md](../MODEL_SPEC.md)를 따른다.
