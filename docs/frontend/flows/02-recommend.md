# [Frontend] AI 추천 대기 + Polling 결과 조회 + 재시도

> 전체 플로우: [docs/flows/02-recommend.md](../../flows/02-recommend.md)

## 요구사항

**상태 조회 polling**
- 페이지 진입 시 `GET /api/user-reviews/{id}`를 호출한다.
- `recommendationStatus == PENDING`이면 대기 UI를 표시하고 polling을 유지한다.
- `recommendationStatus == COMPLETED`이면 `recommendations[]`를 렌더링하고 polling을 중단한다.
- `recommendationStatus == FAILED`이면 에러 메시지와 retry 버튼을 표시하고 polling을 중단한다.
- 페이지 이탈 시 polling timer를 정리한다.

**Polling interval**
- interval 값은 `frontend/src/config/polling.ts`에서 관리한다.
- 초기값은 임시 정책으로 두고, 실제 FastAPI 추천 처리 시간(P50/P90/P99)을 측정한 뒤 조정한다.
- 최대 대기 시간과 timeout UI는 UX 정책에서 별도로 정한다.

**재시도**
- retry 버튼 클릭 시 `POST /api/user-reviews/{id}/retry`를 요청한다.
- 요청 성공 후 `PENDING` UI로 복귀하고 polling을 재개한다.

## 페이지 구성요소

| 구성요소 | 역할 |
|----------|------|
| `ReviewBasedRecommendPage` | 페이지 루트, polling timer 관리, 상태 분기 |
| `RecommendationCard` | 추천 앨범 카드 렌더링 (albumId, reason, url) |
| `RetryButton` | FAILED 상태일 때 노출, retry 요청 처리 |

## 테스트 시나리오

### Unit — [`polling.test.ts`](../../../frontend/src/config/polling.test.ts)

| 시나리오 |
|----------|
| polling interval 계산 |

### Component

| 시나리오 | 테스트 파일 |
|----------|-------------|
| 추천 카드 렌더링 | [`RecommendationCard.test.tsx`](../../../frontend/src/components/RecommendationCard.test.tsx) |
| retry 버튼 렌더링 | [`RetryButton.test.tsx`](../../../frontend/src/components/RetryButton.test.tsx) |

### Page — [`ReviewBasedRecommendPage.test.tsx`](../../../frontend/src/pages/ReviewBasedRecommendPage.test.tsx)

| 시나리오 |
|----------|
| 페이지 진입 |
| PENDING 응답 |
| COMPLETED 응답 |
| FAILED 응답 |
| FAILED 응답만 수신 |
| retry 버튼 클릭 |
| 페이지 이탈 |

### E2E (Playwright)

| 시나리오 | 기댓값 | 테스트 대상 | 테스트 케이스 |
|----------|--------|-------------|---------------|
| PENDING → COMPLETED | 대기 UI 후 추천 카드 렌더링 | E2E | `recommendation_pendingThenCompleted_rendersCards` |

## 관련 API

- [API_SPEC.md — GET /api/user-reviews/{id}](../../API_SPEC.md#get-apiuser-reviewsid)
- [API_SPEC.md — POST /api/user-reviews/{id}/retry](../../API_SPEC.md#post-apiuser-reviewsidretry)

## 분기 로직

```
페이지 진입
  → GET /api/user-reviews/{id}

GET /api/user-reviews/{id} 응답
  → recommendationStatus == PENDING:
      대기 UI 표시
      interval 후 GET /api/user-reviews/{id} 재호출

  → recommendationStatus == COMPLETED:
      recommendations[] 카드 렌더링
      polling 중단

  → recommendationStatus == FAILED:
      에러 + retry 버튼 표시
      polling 중단

retry 버튼 클릭
  → POST /api/user-reviews/{id}/retry
  → PENDING UI 복귀
  → polling 재개
```
