# [Java] 내 감상문 목록 조회

> 전체 플로우: [docs/flows/03-my-reviews.md](../../../flows/03-my-reviews.md)

## 요구사항

- `GET /api/user-reviews?page=0&size=10` 으로 공개 감상문 목록을 페이지네이션으로 반환한다.
- `isPublic=true`인 감상문만 반환한다.
- 최신순(`createdAt` DESC)으로 정렬한다.

## 테스트 시나리오

| 시나리오 | 기댓값 | 테스트 클래스 | 테스트 메서드 |
|----------|--------|---------------|---------------|
| isPublic=true 리뷰 → SummaryResponse로 변환 | result.size()==1, id/trackName 매핑 | `UserReviewServiceTest` | `list_mapToSummaryResponse` |
| 성공 경로 (목록 조회 → 카드 렌더링) | E2E 검증 | Playwright | - |

## 구현 흐름

`UserReviewController`
→ `UserReviewService`
→ `UserReviewRepository`
→ `UserReviewSummaryResponse`

- `UserReviewController`: `GET /api/user-reviews` 수신
- `UserReviewService`: 공개 감상문 목록 조회 및 요약 응답 변환
- `UserReviewRepository`: 공개 감상문 최신순 페이지 조회
- `UserReviewSummaryResponse`: 목록용 응답 DTO 변환

API/DTO/Entity 상세는 [API_SPEC.md](../../API_SPEC.md), [DB_SPEC.md](../DB_SPEC.md)를 따른다.
