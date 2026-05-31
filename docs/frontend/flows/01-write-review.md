# [Frontend] 감상문 작성 + AI 추천 요청

> 전체 플로우: [docs/flows/01-write-review.md](../../flows/01-write-review.md)

## 요구사항

- 감상문 폼을 렌더링한다. 필수 필드: `trackName`, `artistName`, `reviewContent`.
- POST /api/user-reviews 요청 후 응답의 `data.id`로 `/recommend/{id}`로 이동한다.
- 요청 중 로딩 상태를 표시한다.
- 400 에러 수신 시 `message` 필드를 폼 에러로 표시한다.

## 페이지 구성요소

| 구성요소 | 역할 |
|----------|------|
| `WriteReviewPage` | 페이지 루트, 제출 핸들러, navigate 처리 |
| `ReviewForm` | 폼 렌더링, 필드 유효성 검사 |

## 테스트 시나리오

### Component — [`ReviewForm.test.tsx`](../../../frontend/src/components/ReviewForm.test.tsx)

| 시나리오 |
|----------|
| 필수 입력값 렌더링 |
| 선택 입력값 렌더링 |
| 필수 입력값 누락 후 제출 |
| 선택 입력값 없이 제출 |
| 선택 입력값 포함 제출 |

### Page — [`WriteReviewPage.test.tsx`](../../../frontend/src/pages/WriteReviewPage.test.tsx)

| 시나리오 |
|----------|
| 제출 중 상태 |
| 저장 성공 응답 수신 |
| 400 에러 수신 |
| 500 에러 수신 |

### E2E (Playwright)

| 시나리오 | 기댓값 | 테스트 케이스 |
|----------|--------|---------------|
| 성공 경로 (작성 → 저장 → 추천 페이지 이동) | `/recommend/{id}`로 이동 | `writeReview_success_navigatesToRecommend` |

## 관련 API

- [API_SPEC.md — POST /api/user-reviews](../../API_SPEC.md#post-apiuser-reviews)

## 분기 로직

```
POST /api/user-reviews
  → 201: navigate(`/recommend/${data.id}`)
  → 400: message 필드를 폼 에러로 표시
  → 500: 일반 에러 메시지 표시
```
