# ADR-FE001: 상태 소유와 API 응답 처리

## Context

- 백엔드 API는 성공 응답을 하나의 형태로만 반환하지 않는다.
- POST 성공은 `ApiResponse<T>`를 사용하고, GET 조회는 DTO 또는 목록을 직접 반환한다.

API 응답 해석과 화면 상태 소유 기준이 없으면 페이지마다 응답 파싱과 상태 관리 방식이 달라질 수 있다.

---

## Decision 1: API method별 응답 처리 원칙

API 응답 형태는 [API_SPEC.md](../../API_SPEC.md#1-공통-규칙)를 따른다.

API method별로 다음과 같이 처리한다.

| API 유형 | 성공 응답 처리 |
|----------|----------------|
| POST 성공 | `ApiResponse<T>` 사용. `success`, `message`, `data` 확인 |
| GET 단건 | DTO 직접 사용 |
| GET 목록 | 배열 또는 Page 응답 직접 사용 |
| 에러 | `ErrorResponse.message`를 사용자에게 표시 |

화면 분기 로직은 [API_SPEC.md](../../API_SPEC.md)와 [flows](../flows/)에 명시된 프론트 의존 필드만 사용한다.
문서에 없는 백엔드 내부 필드에 기대어 분기하지 않는다.

---

## Decision 2: API 계약 타입 정합성

프론트 타입, fixture, MSW handler는 [API_SPEC.md](../../API_SPEC.md)의 프론트 의존 필드 타입을 따른다.

API 계약과 fixture 타입이 다르면 테스트가 실제 API drift를 잡지 못하므로, 테스트 데이터도 운영 API와 같은 타입을 사용한다.

---

## Decision 3: 서버 상태와 플로우 상태는 Page에서 관리한다

서버 응답 데이터, loading/error, pagination, polling timer, retry loading처럼 API 호출 흐름에 연결된 상태는 Page가 소유한다.
하위 Component는 props와 callback을 통해 렌더링과 사용자 입력 이벤트를 담당한다.

순수 UI local state는 Component가 소유할 수 있다.

| 상태 종류 | 소유 위치 | 예시 |
|----------|-----------|------|
| 서버 상태 | Page | API 응답 데이터, 목록 items, 상세 데이터 |
| 플로우 상태 | Page | submit loading, pagination, polling timer, retry loading |
| 순수 UI local state | Component | input focus, dropdown open, hover, accordion open 여부 |

---

## Decision 4: Page 비동기 상태 모델

Page에서 API 요청 결과가 `loading`, `success`, `notFound`, `error`처럼 서로 배타적인 경우 discriminated union으로 상태를 표현한다.
여러 boolean과 nullable data를 조합하면 불가능한 상태가 생기므로 피한다.

```ts
type PageState<T> =
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "notFound" }
  | { status: "error"; message: string };
```

404는 `notFound`, 500/네트워크 오류/JSON 파싱 실패는 `error`로 분리한다.
route param 또는 요청 key가 변경되면 이전 상태를 `loading`으로 reset한다.
비동기 effect는 cleanup flag 또는 AbortController로 stale response를 무시한다.
요청 중 상태는 성공, HTTP error, 네트워크 오류, JSON 파싱 실패 모든 경로에서 해제되어야 하며, `finally` 또는 동등한 cleanup으로 보장한다.

---

## Consequences

- POST와 GET의 응답 파싱 방식이 섞이지 않는다.
- 프론트 타입과 테스트 fixture가 API 계약과 같은 타입을 사용해 계약 drift를 줄인다.
- 화면 분기 로직은 문서화된 프론트 의존 필드만 사용한다.
- 하위 컴포넌트가 API 호출과 서버/플로우 상태를 직접 소유하지 않는다.
- Page 상태에서 불가능한 조합을 줄이고, 404와 일반 장애를 명확히 분리한다.
- 전역 상태 라이브러리는 현재 범위에서 도입하지 않는다.
