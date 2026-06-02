# [Java] 전문가 리뷰 목록/상세 조회

> 전체 플로우: [docs/flows/04-critics-review.md](../../../flows/04-critics-review.md)

## 요구사항

- `GET /api/critics?page=0&size=10` 으로 페이지네이션 목록을 반환한다.
- `reviewSummary`가 있는 리뷰만 반환한다 (GPT 요약 완료된 것).
- 존재하지 않는 id → `ResourceNotFoundException` (HTTP 404)

## 테스트 시나리오

### DTO — [`DtoFactoryTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/dto/DtoFactoryTest.java)

| 시나리오 |
|----------|
| 전문가 리뷰 목록용 DTO 필드 매핑 |
| 전문가 리뷰 상세용 DTO 필드 매핑 |

### Controller — [`CriticsReviewControllerTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/criticsReview/CriticsReviewControllerTest.java)

| 시나리오 |
|----------|
| 존재하는 id 단건 조회 시 HTTP 200 반환 |
| 존재하지 않는 id 조회 시 HTTP 404와 실패 응답 반환 |

### Service — [`CriticsReviewServiceTest`](../../../backendJava/src/test/java/shop/jazzmate/jazzmateshop/criticsReview/CriticsReviewServiceTest.java)

| 시나리오 |
|----------|
| 전문가 리뷰 첫 페이지 조회 |
| 전문가 리뷰 마지막 페이지 조회 |
| 존재하는 id 단건 조회 |
| 존재하지 않는 id 조회는 예외로 처리 |

### E2E (Playwright, 추후 구현)

| 시나리오 |
|----------|
| 전문가 리뷰 목록 조회 후 카드 렌더링 |
| 전문가 리뷰 상세 조회 후 상세 화면 렌더링 |

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

API/DTO/Entity 상세는 [API_SPEC.md](../../API_SPEC.md), [MODEL_SPEC.md](../MODEL_SPEC.md)를 따른다.
