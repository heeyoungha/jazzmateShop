# [Frontend] 전문가 리뷰 목록/상세 조회

> 전체 플로우: [docs/flows/04-critics-review.md](../../flows/04-critics-review.md)

## 요구사항

- GET /api/critics?page=0&size=10 으로 목록을 가져온다.
- `last == true`이면 무한 스크롤을 종료한다.
- 카드 클릭 시 `/critics/{id}`로 이동한다.
- 상세 페이지 진입 시 GET /api/critics/{id}로 상세를 조회한다.

## 페이지 구성요소

| 구성요소 | 역할 |
|----------|------|
| `CriticsReviewPage` | 목록 페이지 루트, 무한 스크롤 처리 |
| `CriticsReviewDetailPage` | 상세조회 페이지 루트, 단건 조회 및 에러 처리 |
| `CriticsReviewCard` | 리뷰 카드 (title, reviewer, date, reviewSummary 요약) |
| `CriticsReviewDetail` | 상세 뷰 (content, reviewSummary 전체, url) |

## 테스트 시나리오

### Unit (Vitest)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 다음 page 계산 | `last == false`이면 `number+1` 반환 | pagination helper | `getNextCriticsPage_whenNotLast_returnsNextPage` |
| 다음 page 계산 종료 | `last == true`이면 다음 page 없음 | pagination helper | `getNextCriticsPage_whenLast_returnsNull` |

### Component (React Testing Library + Vitest)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 카드 렌더링 | title, reviewer, date, reviewSummary 요약 표시 | `CriticsReviewCard` | `rendersCardSummaryFields` |
| 카드 클릭 | onClick callback 호출 | `CriticsReviewCard` | `click_callsOnClick` |
| 상세 렌더링 | content, reviewSummary 전체, url 표시 | `CriticsReviewDetail` | `rendersDetailFields` |

### Page (React Testing Library + Vitest + MSW + fake timer)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 페이지 진입 | `GET /api/critics?page=0&size=10` 호출 | `CriticsReviewPage` | `mount_fetchesFirstPage` |
| 목록 응답 수신 | `CriticsReviewCard` 목록 렌더링 | `CriticsReviewPage` | `listResponse_rendersCriticsCards` |
| `last == false` 상태에서 스크롤 하단 도달 | `page=number+1` 추가 요청 | `CriticsReviewPage` | `scrollBottom_whenNotLast_fetchesNextPage` |
| `last == true` 상태에서 스크롤 하단 도달 | 추가 요청 없음 | `CriticsReviewPage` | `scrollBottom_whenLast_doesNotFetch` |
| 카드 클릭 | `/critics/{id}`로 이동 | `CriticsReviewPage` | `cardClick_navigatesToDetailPage` |
| 페이지 진입 | `GET /api/critics/{id}` 호출 | `CriticsReviewDetailPage` | `mount_fetchesCriticsDetail` |
| 상세 응답 수신 | 상세 뷰 렌더링 | `CriticsReviewDetailPage` | `detailResponse_showsDetailView` |
| 상세 404 응답 | 에러 메시지 표시 | `CriticsReviewDetailPage` | `detailNotFound_showsErrorMessage` |

### E2E (Playwright)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 성공 경로 (목록 조회 → 상세 조회) | 카드 클릭 후 상세 페이지 표시 | E2E | `criticsReview_listAndOpenDetail` |

## 관련 API

- [API_SPEC.md — GET /api/critics](../../API_SPEC.md#get-apicritics)
- [API_SPEC.md — GET /api/critics/{id}](../../API_SPEC.md#get-apicriticsid)

## 분기 로직

```
스크롤 하단 도달
  → last == false: 추가 요청 (page=number+1)
  → last == true:  요청 중단

카드 클릭
  → /critics/{id}로 이동

상세 페이지 진입
  → GET /api/critics/{id}
  → 상세 렌더링

GET /api/critics/{id} → 404
  → 에러 메시지 표시
```
