# ADR-FE002: 추천 상태 Polling UI

## Context

- 감상문 저장 후 AI 추천은 비동기로 처리된다.
- FastAPI가 추천 결과를 Spring Boot로 콜백하기 전까지 프론트는 추천 완료 여부를 알 수 없다.

현재 공통 설계는 SSE가 아니라 HTTP polling으로 추천 상태를 확인한다.

---

## Decision

`ReviewBasedRecommendPage`는 `GET /api/user-reviews/{id}`를 반복 호출해 `recommendationStatus`를 확인한다.

| 상태 | UI 동작 | polling |
|------|---------|---------|
| `PENDING` | 대기 UI 표시 | 유지 |
| `COMPLETED` | `recommendations[]` 카드 렌더링 | 중단 |
| `FAILED` | 에러 메시지 + retry 버튼 표시 | 중단 |

Polling 규칙:

1. 페이지 진입
   - 즉시 `GET /api/user-reviews/{id}`를 호출한다.
   - 응답의 `recommendationStatus`로 화면을 분기한다.

2. 상태별 분기
   - `PENDING`: 대기 UI를 표시하고 polling을 유지한다.
   - `COMPLETED`: `recommendations[]` 카드를 렌더링하고 polling을 중단한다.
   - `FAILED`: 에러 메시지와 retry 버튼을 노출하고 polling을 중단한다.

3. Retry
   - GET 조회에서 `FAILED` 상태를 받았다고 retry를 자동 호출하지 않는다.
   - retry는 사용자가 `POST /api/user-reviews/{id}/retry`를 명시적으로 호출할 때만 실행한다.

4. Timer cleanup
   - 페이지 이탈 시 timer를 반드시 정리한다.
   - `COMPLETED` 또는 `FAILED`에 도달하면 남아 있는 timer를 중단한다.

5. Interval 정책
   - interval 값은 `frontend/src/config/polling.ts`에서 관리한다.
   - 초기 interval은 임시 정책으로 두고, 실제 FastAPI 추천 처리 시간(P50/P90/P99)을 측정한 뒤 조정한다.
   - 측정 기준은 추천 요청 시작부터 `recommendationStatus`가 `COMPLETED` 또는 `FAILED`로 전이될 때까지의 시간이다.

### Retry 정책 트레이드오프

사용자 명시 retry를 채택한 이유는 무한 재시도 방지, 비용 통제, 상태 모델 단순성 유지를 동시에 만족하기 위해서다.

| 옵션 | 설명 | 채택 여부 | 이유 |
|------|------|-----------|------|
| 사용자 명시 retry | FAILED에서 retry 버튼을 노출하고, 사용자가 클릭할 때만 `POST /retry` 호출 | 채택 | 무한 재시도와 FastAPI 호출 비용 증가를 방지하면서 상태 모델을 단순하게 유지한다. |
| 프론트 자동 retry | GET 응답이 FAILED이면 프론트가 즉시 `POST /retry` 호출 | 기각 | 실패 원인이 지속되면 polling과 결합되어 무한 반복될 수 있다. |
| 백엔드 GET 자동 retry | GET 조회 중 FAILED를 감지하면 서버가 이벤트를 재발행 | 기각 | 조회 API가 상태 변경을 수행하게 되고, 새로고침마다 재시도될 수 있다. |
| 제한된 자동 retry | retry count/backoff로 N회 자동 재시도 | 보류 | retry count 저장과 backoff 정책이 필요해 현재 범위보다 복잡하다. |
| 백그라운드 job retry | scheduler/queue가 실패 추천을 재처리 | 보류 | 운영 인프라와 별도 재시도 정책이 필요하다. |

---

## Consequences

- 프론트는 서버 연결을 오래 유지하지 않는다.
- 새로고침이나 polling 반복만으로 FastAPI 재요청이 발생하지 않는다.
- retry는 사용자 명시 동작으로만 실행된다.
- polling interval과 최대 대기 시간은 UX 정책에 따라 조정할 수 있다.
