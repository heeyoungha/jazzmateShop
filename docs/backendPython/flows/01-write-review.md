# [FastAPI] 감상문 작성 후 추천 요청 수신

> 전체 플로우: [docs/flows/01-write-review.md](../../flows/01-write-review.md)

## 요구사항

- FastAPI는 감상문 저장 자체에는 참여하지 않는다.
- Spring Boot가 트랜잭션 커밋 후 전송하는 `POST /recommend/by-review`를 수신한다.
- 유효한 요청이면 `202 Accepted`를 반환하고 추천 처리를 백그라운드로 시작한다.
- 추천 처리 상세는 [02-recommend.md](./02-recommend.md)를 따른다.

## 책임 경계

| 단계 | 담당 | FastAPI 책임 |
|---|---|---|
| 감상문 폼 제출 | Frontend | 없음 |
| 감상문 저장 | Spring Boot | 없음 |
| 추천 요청 이벤트 발행 | Spring Boot | 없음 |
| 추천 요청 수신 | FastAPI | `review_id`, `review_content` 검증 |
| 추천 처리 시작 | FastAPI | background task 등록 후 202 반환 |

## 테스트 시나리오

### `RecommendRouterTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| Spring 추천 요청 수신 | HTTP 202, background task 등록 | `post_byReview_validRequest_returns202` |
| `review_id` 누락 | HTTP 422 | `post_byReview_missingReviewId_returns422` |
| `review_content` 누락 | HTTP 422 | `post_byReview_missingReviewContent_returns422` |
| `review_content` 공백 | HTTP 422 | `post_byReview_blankReviewContent_returns422` |
| `review_id`가 0 이하 | HTTP 422 | `post_byReview_nonPositiveReviewId_returns422` |

### `RecommendByReviewRequestTest`

| 시나리오 | 기댓값 | 테스트 메서드 |
|----------|--------|---------------|
| 유효한 요청 DTO | `review_id`, `review_content` 매핑 | `validRequest_mapsFields` |
| 공백 포함 본문 | trim 후 non-empty 검증 | `reviewContent_trimsWhitespace` |

## 관련 API

- [API_SPEC.md — POST /recommend/by-review](../../API_SPEC.md#post-recommendby-review)
