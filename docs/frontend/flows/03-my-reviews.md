# [Frontend] 내 감상문 목록 조회

> 전체 플로우: [docs/flows/03-my-reviews.md](../../flows/03-my-reviews.md)

## 요구사항

- GET /api/user-reviews?page=0&size=10 으로 목록을 가져온다.
- 스크롤 하단 도달 시 `page+1` 요청으로 무한 스크롤을 구현한다.
- 각 카드 클릭 시 `/recommend/{id}`로 이동한다.

## 페이지 구성요소

| 구성요소 | 역할 |
|----------|------|
| `MyReviewsPage` | 페이지 루트, 무한 스크롤 처리 |
| `ReviewCard` | 감상문 요약 카드 (trackName, artistName, rating, createdAt) |

## 테스트 시나리오

### Unit — [`pagination.test.ts`](../../../frontend/src/lib/pagination.test.ts)

| 시나리오 |
|----------|
| 마지막 페이지가 아니면 다음 페이지 번호를 반환한다 |
| 마지막 페이지이면 null을 반환한다 |

### Component — [`ReviewCard.test.tsx`](../../../frontend/src/components/ReviewCard.test.tsx)

| 시나리오 |
|----------|
| 카드 렌더링 |
| 카드 클릭 |

### Page — [`MyReviewsPage.test.tsx`](../../../frontend/src/pages/MyReviewsPage.test.tsx)

| 시나리오 |
|----------|
| 페이지 진입 |
| 목록 응답 수신 |
| 빈 목록 응답 |
| `last == false` 상태에서 스크롤 하단 도달 |
| `last == true` 상태에서 스크롤 하단 도달 |
| 추가 응답 수신 |
| 카드 클릭 |

### E2E (Playwright)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 성공 경로 (목록 조회 → 카드 클릭) | 카드 표시 후 `/recommend/{id}` 이동 | E2E | `myReviews_listAndNavigateToRecommend` |

## 관련 API

- [API_SPEC.md — GET /api/user-reviews](../../API_SPEC.md#get-apiuser-reviews)

## 분기 로직

```
스크롤 하단 도달
  → last == false: 추가 요청 (page=number+1)
  → last == true: 요청 중단
  → 응답 데이터 기존 목록에 append

빈 목록
  → 빈 상태 메시지 표시
```
