# [Java] 전문가 리뷰 목록/상세 조회

> 전체 플로우: [docs/flows/04-critics-review.md](../../../flows/04-critics-review.md)

## 요구사항

- `GET /api/critics?page=0&size=10` 으로 페이지네이션 목록을 반환한다.
- `reviewSummary`가 있는 리뷰만 반환한다 (GPT 요약 완료된 것).
- 존재하지 않는 id → `ResourceNotFoundException` (HTTP 404)

## 테스트 시나리오

### `DtoFactoryTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 목록용 DTO 필드 매핑 | id/title/reviewer/date/reviewSummary만 매핑 | `from_mapsOnlySummaryFields` |
| 상세용 DTO 필드 매핑 | id/title/reviewer/date/content/reviewSummary/url/createdAt 매핑 | `from_mapsOnlyDetailFields` |

### `CriticsReviewControllerTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 존재하는 id 단건 조회 → HTTP 200 | HTTP 200 | `getReview_existingId_returnsDetailResponse` |
| 존재하지 않는 id → HTTP 404, success=false | success=false | `getReview_notFound_returns404` |

### `CriticsReviewServiceTest`

| 시나리오 | 기댓값 | 테스트 클래스 | 테스트 메서드 |
|----------|--------|---------------|---------------|
| 15건 중 page=0&size=10 조회 | content.size()==10, last==false | `CriticsReviewServiceTest` | `getReviews_firstPage_returnsPageWithLastFalse` |
| 15건 중 page=1&size=10 조회 | content.size()==5, last==true | `CriticsReviewServiceTest` | `getReviews_lastPage_returnsPageWithLastTrue` |
| 존재하는 id 단건 조회 | CriticsReview 반환 | `CriticsReviewServiceTest` | `getReview_existingId_returnsCriticsReview` |
| 존재하지 않는 id → 예외 | ResourceNotFoundException | `CriticsReviewServiceTest` | `getReview_notFound_throwsResourceNotFoundException` |

## 구현 흐름

`CriticsReviewController`
→ `CriticsReviewService`
→ `CriticsReviewRepository`
→ `CriticsReview`

- `CriticsReviewController`: `GET /api/critics`, `GET /api/critics/{id}` 수신, DTO 반환
- `CriticsReviewService`: 전문가 리뷰 목록/단건 조회 및 DTO 변환
- `CriticsReviewSummaryResponse`: 목록용 응답 DTO
- `CriticsReviewResponse`: 상세용 응답 DTO
- `CriticsReviewRepository`: GPT 요약 완료 리뷰 조회
- `CriticsReview`: 읽기 전용 Entity

API/DTO/Entity 상세는 [API_SPEC.md](../../API_SPEC.md), [DB_SPEC.md](../DB_SPEC.md)를 따른다.
