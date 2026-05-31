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

### Unit — [`pagination.test.ts`](../../../frontend/src/lib/pagination.test.ts)

| 시나리오 |
|----------|
| 마지막 페이지가 아니면 다음 페이지 번호를 반환한다 |
| 마지막 페이지이면 null을 반환한다 |

### Component

| 시나리오 | 테스트 파일 |
|----------|-------------|
| 카드 렌더링 | [`CriticsReviewCard.test.tsx`](../../../frontend/src/components/CriticsReviewCard.test.tsx) |
| 카드 클릭 | [`CriticsReviewCard.test.tsx`](../../../frontend/src/components/CriticsReviewCard.test.tsx) |
| 상세 렌더링 | [`CriticsReviewDetail.test.tsx`](../../../frontend/src/components/CriticsReviewDetail.test.tsx) |

### Page

| 시나리오 | 테스트 파일 |
|----------|-------------|
| 페이지 진입 (목록) | [`CriticsReviewPage.test.tsx`](../../../frontend/src/pages/CriticsReviewPage.test.tsx) |
| 목록 응답 수신 | [`CriticsReviewPage.test.tsx`](../../../frontend/src/pages/CriticsReviewPage.test.tsx) |
| `last == false` 상태에서 스크롤 하단 도달 | [`CriticsReviewPage.test.tsx`](../../../frontend/src/pages/CriticsReviewPage.test.tsx) |
| `last == true` 상태에서 스크롤 하단 도달 | [`CriticsReviewPage.test.tsx`](../../../frontend/src/pages/CriticsReviewPage.test.tsx) |
| 카드 클릭 | [`CriticsReviewPage.test.tsx`](../../../frontend/src/pages/CriticsReviewPage.test.tsx) |
| 페이지 진입 (상세) | [`CriticsReviewDetailPage.test.tsx`](../../../frontend/src/pages/CriticsReviewDetailPage.test.tsx) |
| 상세 응답 수신 | [`CriticsReviewDetailPage.test.tsx`](../../../frontend/src/pages/CriticsReviewDetailPage.test.tsx) |
| 상세 404 응답 | [`CriticsReviewDetailPage.test.tsx`](../../../frontend/src/pages/CriticsReviewDetailPage.test.tsx) |

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
