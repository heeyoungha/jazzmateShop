# [Java] AI 추천 처리 + Polling 결과 조회 + 재시도

> 전체 플로우: [docs/flows/02-recommend.md](../../../flows/02-recommend.md)

## 요구사항

**콜백 수신**
- 중복 저장 방지: DB UNIQUE 제약(`uq_recommend_album_review_album`)에 위임.
- `saveAll()`로 하나의 트랜잭션에서 일괄 저장한다. 중복은 DB UNIQUE 제약 기준으로 감지하고 서비스에서 조용히 스킵한다.
- 저장 완료 후 `recommendationStatus = COMPLETED`로 전이한다.

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
- 존재하지 않는 id → `ResourceNotFoundException` (HTTP 404)
- GET 조회에서는 FAILED 상태여도 retry를 자동 실행하지 않는다. retry는 이 API를 호출했을 때만 실행한다.

## 테스트 시나리오

**콜백 저장**

| 시나리오 | 기댓값 | 테스트 클래스 | 테스트 메서드 |
|----------|--------|---------------|---------------|
| 1건 저장 → `saveAll()` 1건 호출 | 저장 목록 size==1 | `RecommendAlbumServiceTest` | `createRecommendAlbums_oneItem_savesBatch` |
| 3건 저장 → `saveAll()` 3건 호출 | 저장 목록 size==3 | `RecommendAlbumServiceTest` | `createRecommendAlbums_threeItems_savesBatch` |
| 콜백 저장 완료 → 대상 리뷰 상태 COMPLETED 전이 | status=COMPLETED | `RecommendAlbumServiceTest` | `createRecommendAlbums_marksReviewCompleted` |
| 존재하지 않는 reviewId → 예외 | ResourceNotFoundException | `RecommendAlbumServiceTest` | `createRecommendAlbums_reviewNotFound_throwsResourceNotFoundException` |
| 성공 경로 (콜백 수신 → saveAll → polling 조회에서 COMPLETED 확인) | E2E 검증 | Playwright | - |

**결과 조회**

| 시나리오 | 기댓값 | 테스트 클래스 | 테스트 메서드 |
|----------|--------|---------------|---------------|
| COMPLETED → recommendations 비어있지 않음, hasRecommendations=true | isHasRecommendations=true, recommendations 비어있지 않음, publishEvent 0회 | `UserReviewServiceTest` | `getById_completed_returnsRecommendations` |
| PENDING → recommendations 빈 리스트, 이벤트 미발행 | status=PENDING, recommendations=[], publishEvent 0회 | `UserReviewServiceTest` | `getById_pending_noEventPublished` |
| FAILED → recommendations 빈 리스트, 이벤트 미발행 | status=FAILED, recommendations=[], publishEvent 0회 | `UserReviewServiceTest` | `getById_failed_noEventPublished` |
| 존재하지 않는 id → 예외 | ResourceNotFoundException | `UserReviewServiceTest` | `getById_notFound_throwsResourceNotFoundException` |
| retry: FAILED → PENDING 전이 + 이벤트 재발행 | status=PENDING, publishEvent 1회 | `UserReviewServiceTest` | `retry_failed_changesPendingAndPublishesEvent` |
| retry: 존재하지 않는 id → 예외 | ResourceNotFoundException | `UserReviewServiceTest` | `retry_notFound_throwsResourceNotFoundException` |
| 컨트롤러: 존재하지 않는 id → HTTP 404, success=false | success=false | `UserReviewControllerTest` | `getById_notFound_returns404` |
| ResourceNotFoundException → 404, success=false, message 포함 | success=false, message 포함 | `GlobalExceptionHandlerTest` | `resourceNotFound_returns404` |
| 성공 경로 (PENDING polling → COMPLETED → recommendations 카드 렌더링) | E2E 검증 | Playwright | - |

## 구현 흐름

**콜백 저장**

`RecommendAlbumController`
→ `RecommendAlbumService`
→ `RecommendAlbumRepository`
→ `UserReview`

- `RecommendAlbumController`: FastAPI 콜백 수신
- `RecommendAlbumService`: 추천 결과 변환, 일괄 저장, 감상문 상태 `COMPLETED` 전이
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

API/DTO/Entity 상세는 [API_SPEC.md](../../API_SPEC.md), [DB_SPEC.md](../DB_SPEC.md)를 따른다.
