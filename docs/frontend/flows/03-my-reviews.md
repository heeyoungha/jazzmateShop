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

### Unit (Vitest)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 다음 page 계산 | `last == false`이면 `number+1` 반환 | pagination helper | `getNextReviewPage_whenNotLast_returnsNextPage` |
| 다음 page 계산 종료 | `last == true`이면 다음 page 없음 | pagination helper | `getNextReviewPage_whenLast_returnsNull` |

### Component (React Testing Library + Vitest)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 카드 렌더링 | trackName, artistName, rating, createdAt 표시 | `ReviewCard` | `rendersSummaryFields` |
| 카드 클릭 | onClick callback 호출 | `ReviewCard` | `click_callsOnClick` |

### Page (React Testing Library + Vitest + MSW + fake timer)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 페이지 진입 | `GET /api/user-reviews?page=0&size=10` 호출 | `MyReviewsPage` | `mount_fetchesFirstPage` |
| 목록 응답 수신 | `ReviewCard` 목록 렌더링 | `MyReviewsPage` | `listResponse_rendersReviewCards` |
| 빈 목록 응답 | 빈 상태 메시지 표시 | `MyReviewsPage` | `emptyList_showsEmptyState` |
| `last == false` 상태에서 스크롤 하단 도달 | `page=number+1` 추가 요청 | `MyReviewsPage` | `scrollBottom_whenNotLast_fetchesNextPage` |
| `last == true` 상태에서 스크롤 하단 도달 | 추가 요청 없음 | `MyReviewsPage` | `scrollBottom_whenLast_doesNotFetch` |
| 추가 응답 수신 | 기존 목록에 append | `MyReviewsPage` | `nextPage_appendsItems` |
| 카드 클릭 | `/recommend/{id}`로 이동 | `MyReviewsPage` | `cardClick_navigatesToRecommendPage` |

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
