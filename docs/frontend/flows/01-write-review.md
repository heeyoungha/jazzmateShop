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

### Component (React Testing Library + Vitest)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 필수 입력값 렌더링 | trackName, artistName, reviewContent 입력 필드 표시 | `ReviewForm` | `rendersRequiredFields` |
| 선택 입력값 렌더링 | rating, mood, genre, energyLevel, bpm, vocalStyle, instrumentation, isPublic 입력 UI 표시 | `ReviewForm` | `rendersOptionalFields` |
| 필수 입력값 누락 후 제출 | API 호출 없음, 폼 에러 표시 | `ReviewForm` | `submit_missingRequiredFields_showsValidationErrors` |
| 선택 입력값 없이 제출 | 필수 필드만으로 submit 가능 | `ReviewForm` | `submit_withoutOptionalFields_allowsSubmit` |
| 선택 입력값 포함 제출 | 선택 필드 입력값이 submit payload에 포함됨 | `ReviewForm` | `submit_withOptionalFields_includesOptionalValues` |

### Page (React Testing Library + Vitest + MSW + fake timer)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 제출 중 상태 | submit 버튼 비활성화, loading 표시 | `WriteReviewPage` | `submit_pending_disablesSubmitButton` |
| 저장 성공 응답 수신 | `data.id`로 `/recommend/{id}` 이동 | `WriteReviewPage` | `submit_success_navigatesToRecommendPage` |
| 400 에러 수신 | `message`를 폼 에러로 표시 | `WriteReviewPage` | `submit_badRequest_showsFormErrorMessage` |
| 500 에러 수신 | 일반 에러 메시지 표시 | `WriteReviewPage` | `submit_serverError_showsGenericErrorMessage` |

### E2E (Playwright)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| 성공 경로 (작성 → 저장 → 추천 페이지 이동) | `/recommend/{id}`로 이동 | E2E | `writeReview_success_navigatesToRecommend` |

## 관련 API

- [API_SPEC.md — POST /api/user-reviews](../../API_SPEC.md#post-apiuser-reviews)

## 분기 로직

```
POST /api/user-reviews
  → 201: navigate(`/recommend/${data.id}`)
  → 400: message 필드를 폼 에러로 표시
  → 500: 일반 에러 메시지 표시
```
