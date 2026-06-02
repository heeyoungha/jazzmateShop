# [Java] AI 추천 처리 + Polling 결과 조회 + 재시도

> 전체 플로우: [docs/flows/02-recommend.md](../../../flows/02-recommend.md)

## 요구사항

**콜백 수신**
- FastAPI는 성공/실패 모두 `POST /api/user-reviews/{id}/recommendations`로 처리 결과를 콜백한다.
- `status=COMPLETED`이면 추천 결과를 `saveAll()`로 하나의 트랜잭션에서 일괄 저장한다.
- 중복 저장 방지: DB UNIQUE 제약(`uq_recommend_album_review_album`)에 위임.
- 저장 완료 후 `recommendationStatus = COMPLETED`로 전이한다.
- `status=FAILED`이면 추천 결과를 저장하지 않고 `recommendationStatus = FAILED`로 전이한다.

**결과 조회 polling**
- 프론트는 `GET /api/user-reviews/{id}`를 주기적으로 호출한다.
- `recommendationStatus`에 따라 응답을 분기한다.
  - `COMPLETED` → `recommendAlbumRepository`에서 추천 목록 반환
  - `PENDING` → 빈 추천 목록 반환, 이벤트 재발행 없음
  - `FAILED` → 빈 추천 목록 반환, retry 자동 재시도 없음
- GET 조회는 상태를 변경하지 않는 read-only 동작이어야 한다.

**재시도**
- `POST /api/user-reviews/{id}/retry` — FAILED 상태에서 사용자가 명시적으로 재시도 요청
- `recommendationStatus = PENDING` 전이 후 `RecommendationRequestEvent` 재발행
- 성공 응답은 `ApiResponse<Void>`로 래핑한다.
- 존재하지 않는 id → `ResourceNotFoundException` (HTTP 404)
- GET 조회에서는 FAILED 상태여도 retry를 자동 실행하지 않는다. retry는 이 API를 호출했을 때만 실행한다.

## 테스트 시나리오

### DTO — [`RecommendAlbumBatchRequestTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/recommendation/dto/RecommendAlbumBatchRequestTest.java)

| 시나리오 |
|----------|
| COMPLETED 콜백 JSON을 Spring Request DTO로 매핑 |
| FAILED 콜백 JSON을 Spring Request DTO로 매핑 |

### Controller — [`RecommendAlbumControllerTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/recommendation/RecommendAlbumControllerTest.java)

| 시나리오 |
|----------|
| COMPLETED 콜백 수신 시 HTTP 200과 빈 body 반환, 서비스 위임 |
| FAILED 콜백 수신 시 HTTP 200과 빈 body 반환, 서비스 위임 |

### Service — [`RecommendAlbumServiceTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/recommendation/RecommendAlbumServiceTest.java)

| 시나리오 |
|----------|
| 추천 item 1건을 저장 엔티티 1건으로 변환하고 일괄 저장 |
| 추천 item 3건을 저장 엔티티 3건으로 변환하고 일괄 저장 |
| COMPLETED 콜백 저장 완료 후 대상 감상문 상태를 COMPLETED로 전이 |
| FAILED 콜백 수신 시 추천 결과를 저장하지 않고 대상 감상문 상태를 FAILED로 전이 |
| 존재하지 않는 reviewId 콜백은 예외로 처리 |

### Service — [`UserReviewServiceTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewServiceTest.java)

| 시나리오 |
|----------|
| COMPLETED 상태 조회는 추천 목록과 `hasRecommendations=true` 반환 |
| PENDING 상태 조회는 빈 추천 목록을 반환하고 이벤트를 재발행하지 않음 |
| FAILED 상태 조회는 빈 추천 목록을 반환하고 retry를 자동 실행하지 않음 |
| 존재하지 않는 id 조회는 예외로 처리 |
| FAILED 상태에서 retry 요청 시 PENDING으로 전이하고 추천 요청 이벤트 재발행 |
| 존재하지 않는 id에 대한 retry 요청은 예외로 처리 |

### Controller — [`UserReviewControllerTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/userReview/UserReviewControllerTest.java)

| 시나리오 |
|----------|
| retry 성공 응답은 `ApiResponse<Void>`로 래핑 |
| retry 대상이 존재하지 않으면 HTTP 404와 실패 응답 반환 |
| 조회 대상이 존재하지 않으면 HTTP 404와 실패 응답 반환 |

### E2E (Playwright, 추후 구현)

| 시나리오 |
|----------|
| 콜백 수신, 저장, polling 조회에서 COMPLETED 확인 |
| PENDING polling, COMPLETED 전이, 추천 카드 렌더링 |

## 구현 흐름

**콜백 저장**

`RecommendAlbumController`
→ `RecommendAlbumService`
→ `RecommendAlbumRepository`
→ `UserReview`

- `RecommendAlbumController`: FastAPI 처리 결과 콜백 수신
- `RecommendAlbumService`: `COMPLETED`이면 추천 결과 변환/일괄 저장 후 감상문 상태 `COMPLETED` 전이, `FAILED`이면 저장 없이 감상문 상태 `FAILED` 전이
- `RecommendAlbumRepository`: 추천 결과 저장
- `UserReview`: 추천 처리 상태 변경

**결과 조회**

`UserReviewController`
→ `UserReviewService`
→ `UserReviewRepository`
→ `RecommendAlbumRepository`

- `UserReviewController`: `GET /api/user-reviews/{id}` 수신
- `UserReviewService`: 감상문 조회, `recommendationStatus`별 응답 분기
- `UserReviewRepository`: 감상문 단건 조회
- `RecommendAlbumRepository`: `COMPLETED` 상태일 때 추천 목록 조회

**재시도**

`UserReviewController`
→ `UserReviewService`
→ `UserReview`
→ `RecommendationEventListener`

- `UserReviewController`: `POST /api/user-reviews/{id}/retry` 수신
- `UserReviewService`: `FAILED` 검증, `PENDING` 전이, 이벤트 재발행
- `UserReview`: `retryRecommendation()`으로 상태 전이
- `RecommendationEventListener`: 재발행된 이벤트를 커밋 후 처리

API/DTO/Entity 상세는 [API_SPEC.md](../../API_SPEC.md), [MODEL_SPEC.md](../MODEL_SPEC.md)를 따른다.
