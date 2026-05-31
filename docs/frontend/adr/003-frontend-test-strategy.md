# ADR-FE003: 프론트엔드 테스트 전략

## Context

프론트엔드는 폼 입력, API 응답 분기, polling timer, retry, 라우팅을 검증해야 한다.
모든 케이스를 Playwright E2E로만 검증하면 테스트가 느리고, 실패 원인을 좁히기 어렵다.
반대로 컴포넌트 테스트만으로는 실제 사용자 플로우와 라우팅을 충분히 검증하기 어렵다.

---

## Decision

테스트는 빠른 단위부터 느린 E2E 순서로 작성한다.

| Phase | 도구 | 검증 대상 | 외부 의존성 |
|-------|------|-----------|-------------|
| Phase 1 | Vitest | config, 순수 함수, API response parser | 없음 |
| Phase 2 | React Testing Library + Vitest | 단일 Component 렌더링, 폼 입력, 버튼 상태, 상태별 UI, custom hook | 없음 또는 props/callback stub |
| Phase 3 | React Testing Library + Vitest + MSW + fake timer | Page 상태 분기, 여러 컴포넌트 조합, polling timer, retry, 에러 처리 | API/timer mock |
| Phase 4 | Playwright | 실제 사용자 플로우, 라우팅, 핵심 API 연동 흐름 | 테스트 서버 또는 MSW handler 재사용 |

---

## Phase 경계

- Phase 1은 React 렌더링 없이 실행 가능한 순수 로직을 검증한다.
- Phase 2는 단일 Component 또는 custom hook을 검증한다. API 호출, router, timer 같은 외부 의존성은 직접 다루지 않는다.
- Phase 3은 Page 단위 조합을 검증한다. 여러 Component가 함께 동작하며, API 응답과 timer는 mock한다.
- Phase 4는 브라우저에서 사용자 관점의 핵심 경로를 검증한다. 세부 상태 조합은 Phase 2/3에서 검증한다.

---

## API Mock 전략

Page 테스트의 API mock은 MSW(Mock Service Worker)를 기본으로 사용한다.

| 옵션 | 특징 | 결정 |
|------|------|------|
| `vi.mock('fetch')` 또는 axios mock | 빠르고 단순하지만 네트워크 계층을 우회한다. 테스트별 mock이 흩어지기 쉽다. | 기각 |
| MSW | 실제 네트워크 요청 계층에서 가로채며, RTL/Vitest와 Playwright에서 handler를 재사용할 수 있다. | 채택 |

MSW handler는 [API_SPEC.md](../../API_SPEC.md) 응답 형태와 동일하게 작성한다.
- API mock 응답은 handler 파일에서 중앙 관리하고, 테스트별 임의 응답 shape를 만들지 않는다.
- 기본 handler는 `defaultHandlers` 안에 둔다.
- 특정 테스트에서 `server.use(...)`로 기본 응답을 덮어써야 하는 경우에만 별도 named handler로 export한다.
- override handler도 request log, page query parsing 등 기본 handler와 같은 관찰 지점을 유지해야 한다.
- fixture와 MSW handler의 id 타입은 API 명세의 실제 타입을 사용한다. UUID/string id를 number로 대체하지 않는다.

---

## Page 비동기 상태 테스트

Page 테스트는 성공, 404, 500, 네트워크 실패를 분리해 검증한다.
route param 기반 조회 Page는 API 명세의 실제 id 타입을 fixture에 사용한다.
상태 reset 또는 stale response 방어 로직을 추가한 경우 해당 동작을 Page 테스트로 고정한다.

404는 찾을 수 없음 UI를 검증하고, 500/네트워크 오류/JSON 파싱 오류는 일반 장애 UI를 검증한다.
`!res.ok` 전체가 같은 UI로 처리되지 않도록 테스트 케이스를 분리한다.

---

## Fake Timer 전략

`setTimeout`/`setInterval` 기반 동작을 검증하는 Page 테스트는 `vi.useFakeTimers()`를 사용한다.
추천 결과 페이지는 `PENDING` 응답을 받으면 일정 interval 뒤 `GET /api/user-reviews/{id}`를 다시 호출하는 polling 구조다.
따라서 테스트에서 timer를 사용하는 목적은 화면에 시간 표시를 검증하기 위해서가 아니라, 실제 시간을 기다리지 않고 다음 동작을 검증하기 위해서다.

- `PENDING`이면 interval 이후 상세 조회를 다시 호출한다.
- `COMPLETED` 또는 `FAILED`이면 추가 polling을 중단한다.
- retry 성공 후 다시 `PENDING` 상태로 돌아가 polling을 재개한다.
- 페이지 언마운트 시 예약된 timer를 정리한다.

timer를 진행할 때는 React state update가 반영되도록 `act(...)` 안에서 `vi.advanceTimersByTimeAsync(...)`를 호출한다.

```ts
async function advanceTimers(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}
```

fake timer를 사용하는 테스트에서는 timer를 명시적으로 진행한 뒤 `getBy*`로 즉시 검증한다.
`findBy*`/`waitFor`는 내부 재시도 timer가 fake timer의 영향을 받아 timeout이 날 수 있으므로, timer 진행 자체를 검증하는 테스트에서는 우선 사용하지 않는다.

```ts
vi.useFakeTimers();
render(<Page />);

await advanceTimers(0);
expect(screen.getByText("추천을 준비하고 있습니다.")).toBeInTheDocument();

await advanceTimers(RECOMMENDATION_POLLING_INTERVAL_MS);
expect(requestLog.reviewDetail).toBe(2);
```

`userEvent`와 fake timer를 함께 쓰면 user-event 내부 delay도 fake timer에 묶일 수 있다.
복잡한 사용자 입력은 `userEvent.setup({ advanceTimers: vi.advanceTimersByTime })`를 사용하고, 단순 버튼 클릭만 검증하는 timer 테스트는 `fireEvent.click`을 허용한다.

---

## 커버리지 기준

초기 기준은 Phase 1~3에 적용한다.
Playwright E2E는 라인 커버리지 목표에 포함하지 않고, 핵심 사용자 경로 통과 여부를 본다.

| 대상 | 기준 |
|------|------|
| Phase 1~3 | line coverage 80% 이상 |
| Phase 4 | 핵심 사용자 플로우 통과 |

커버리지 기준은 프론트 코드 규모와 테스트 안정성이 확인된 뒤 조정할 수 있다.

---

## 원칙

1. 테스트 범위 분리
   - 상태 조합은 React Testing Library + Vitest에서 검증한다.
   - Playwright는 핵심 사용자 경로만 검증한다.
   - E2E는 사용자 관점의 성공/실패 핵심 경로를 검증하고, 세부 상태 조합을 중복 검증하지 않는다.

2. 시간 기반 로직
   - polling interval 계산은 Vitest 단위 테스트로 검증한다.
   - polling timer와 cleanup은 fake timer로 검증한다.
   - fake timer를 진행할 때는 `act + advanceTimersByTimeAsync` 패턴을 사용한다.

3. Custom hook
   - custom hook은 `renderHook`으로 검증하고 Phase 2에 둔다.
   - API/timer와 결합된 hook은 Phase 3 기준을 따른다.

4. API mock
   - API mock 응답은 MSW handler로 관리한다.
   - MSW handler는 [API_SPEC.md](../../API_SPEC.md)와 동일한 응답 형태를 사용한다.
   - fixture id 타입도 API 명세와 동일하게 유지한다.

---

## 구현 순서

1. Config/순수 함수 테스트를 먼저 작성한다.
2. Component/custom hook 테스트로 렌더링, 사용자 입력, hook 상태를 검증한다.
3. Page 테스트로 MSW API 응답별 상태 분기와 timer 동작을 검증한다.
4. Playwright E2E로 실제 라우팅과 사용자 플로우를 검증한다.

---

## Consequences

- 실패 원인을 Unit, Component/Page, E2E 단계별로 좁힐 수 있다.
- polling과 retry 같은 시간 기반 로직을 빠른 테스트에서 안정적으로 검증할 수 있다.
- MSW handler로 API mock 응답을 중앙 관리해 API 계약 drift를 줄인다.
- E2E 테스트 수를 핵심 플로우 중심으로 유지해 실행 시간을 줄인다.
